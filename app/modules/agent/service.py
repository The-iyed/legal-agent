from typing import Any, Dict, Optional, List
import logging
from app.schemas.agent import QueryResponse, FileUploadResponse, StatementOfClaim, FileInfoResponse
from app.modules.semantic_kernel.supervisor import Supervisor
from app.modules.message.service import MessageService
from app.schemas.message import MessageCreate
from app.core.config.settings import get_settings
from azure.storage.blob import BlobServiceClient
from fastapi.responses import StreamingResponse
import json
import uuid
from datetime import datetime
import os
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class AgentService:
    def __init__(self, db: Any, message_service: MessageService):
        self.db = db
        self.supervisor = Supervisor()
        self.message_service = message_service
        self.settings = get_settings()
        logger.info("AgentService initialized")

    async def query_agent(self, query: str, conversation_id: str, user_id: str = None) -> QueryResponse:
        """Main method to handle user queries through the agent system."""
        try:
            # 1. Store user message
            await self._store_user_message(query, conversation_id, user_id)
            
            # 2. Get conversation history
            conversation_history = await self._get_conversation_history(conversation_id)
            
            # 3. Get agent response
            supervisor_result = await self.supervisor.route_query(query=query, context=conversation_history)
            
            # 4. Extract and parse response
            response_content, agent_metadata = self._extract_response_data(supervisor_result)
            
            # 5. Store agent response
            await self._store_agent_message(response_content, agent_metadata, conversation_id, supervisor_result)
            
            # 6. Build API response
            return self._build_api_response(response_content, supervisor_result, agent_metadata)
            
        except Exception as e:
            logger.error(f"Error in query_agent: {str(e)}")
            return QueryResponse(
                response="I apologize, but I encountered an error processing your request.",
                metadata={"error": str(e)}
            )

    async def process_file_upload(self, file_content: bytes, filename: str, conversation_id: str, user_id: str) -> FileUploadResponse:
        """Process file upload, extract data, and validate against statement of claim format."""
        try:
            # 1. Upload file to Azure Blob Storage
            file_url = await self._upload_file_to_blob(file_content, filename, conversation_id)
            
            # 2. Extract text and data from file
            extracted_data = await self._extract_document_data(file_content, filename)
            
            # 3. Validate against statement of claim format
            is_valid, validation_score, validation_errors = await self._validate_statement_of_claim(extracted_data)
            
            # 4. Store user message about file upload
            await self._store_file_upload_message(filename, conversation_id, user_id)
            
            # 5. Store extracted data in database if valid
            case_number = None
            if is_valid:
                await self._store_statement_of_claim(conversation_id, file_url, extracted_data)
                case_number = self._extract_case_number(extracted_data)
            
            # 6. Generate response message
            response_message = await self._generate_file_processing_response(
                is_valid, case_number, validation_errors, conversation_id, extracted_data
            )
            
            # 7. Store agent response
            await self._store_agent_message(
                response_message, 
                {"query_type": "file", "file_processed": True, "is_valid": is_valid}, 
                conversation_id, 
                {"agent_type": "file_processor", "confidence": validation_score}
            )
            
            return FileUploadResponse(
                response=response_message,
                file_url=file_url,
                case_number=case_number,
                is_valid=is_valid,
                metadata={
                    "document_type": extracted_data.get("document_type", "unknown"),
                    "validation_score": validation_score,
                    "validation_errors": validation_errors,
                    "total_pages": extracted_data.get("total_pages", 1)
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing file upload: {str(e)}")
            error_message = "عذراً، حدث خطأ أثناء معالجة الملف. يرجى المحاولة مرة أخرى."
            await self._store_agent_message(
                error_message,
                {"query_type": "file", "file_processed": False, "error": str(e)},
                conversation_id,
                {"agent_type": "file_processor", "confidence": 0.0}
            )
            return FileUploadResponse(
                response=error_message,
                is_valid=False,
                metadata={"error": str(e)}
            )

    async def get_statement_of_claim(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve statement of claim data for a conversation."""
        try:
            statement = await self.db.statement_of_claim.find_one({"conversation_id": conversation_id})
            if statement:
                statement["_id"] = str(statement["_id"])
                return statement
            return None
        except Exception as e:
            logger.error(f"Error retrieving statement of claim: {str(e)}")
            return None

    async def generate_file_download_link(self, statement_data: Dict[str, Any]) -> FileInfoResponse:
        """Generate file information and download link for a statement of claim."""
        try:
            file_url = statement_data.get("file_url", "")
            if not file_url:
                raise ValueError("No file URL found in statement data")
            
            # Parse the blob URL to get filename
            parsed_url = urlparse(file_url)
            filename = os.path.basename(parsed_url.path)
            if not filename:
                filename = f"document_{statement_data.get('conversation_id', 'unknown')}.pdf"
            
            # Generate download URL
            base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
            download_url = f"{base_url}/agents/file/{statement_data.get('conversation_id')}/download"
            
            # Extract case number
            case_number = self._extract_case_number(statement_data)
            
            # Get file metadata
            file_metadata = await self._get_file_metadata(file_url)
            
            return FileInfoResponse(
                conversation_id=statement_data.get("conversation_id", ""),
                file_url=file_url,
                download_url=download_url,
                filename=filename,
                file_size=file_metadata.get("size"),
                content_type=file_metadata.get("content_type", "application/pdf"),
                upload_date=statement_data.get("created_at", datetime.utcnow()),
                case_number=case_number,
                document_type=statement_data.get("document_type", ""),
                validation_score=statement_data.get("validation_score", 0.0),
                is_valid=statement_data.get("is_valid", False),
                total_pages=statement_data.get("total_pages", 1),
                metadata={
                    "extracted_fields_count": len(statement_data.get("extracted_fields", [])),
                    "processing_status": statement_data.get("processing_status", "unknown"),
                    "validation_errors_count": len(statement_data.get("validation_errors", []))
                }
            )
            
        except Exception as e:
            logger.error(f"Error generating file download link: {str(e)}")
            raise

    async def stream_file_content(self, statement_data: Dict[str, Any]) -> StreamingResponse:
        """Stream file content from Azure Blob Storage."""
        try:
            file_url = statement_data.get("file_url", "")
            if not file_url:
                raise ValueError("No file URL found in statement data")
            
            # Parse the blob URL to get container and blob name
            parsed_url = urlparse(file_url)
            path_parts = parsed_url.path.strip('/').split('/')
            
            if len(path_parts) < 2:
                raise ValueError("Invalid blob URL format")
            
            container_name = path_parts[0]
            blob_name = '/'.join(path_parts[1:])
            
            # Initialize blob service client
            blob_service_client = BlobServiceClient.from_connection_string(
                self.settings.AZURE_STORAGE_CONNECTION_STRING
            )
            
            # Get blob client
            blob_client = blob_service_client.get_blob_client(container_name, blob_name)
            
            # Get blob properties
            blob_properties = blob_client.get_blob_properties()
            
            # Determine content type
            content_type = blob_properties.content_settings.content_type or "application/pdf"
            
            # Get filename
            filename = os.path.basename(blob_name)
            if not filename:
                filename = f"document_{statement_data.get('conversation_id', 'unknown')}.pdf"
            
            # Create streaming response
            async def file_generator():
                try:
                    # Download blob in chunks
                    download_stream = blob_client.download_blob()
                    async for chunk in download_stream.chunks():
                        yield chunk
                except Exception as e:
                    logger.error(f"Error streaming file content: {str(e)}")
                    raise
            
            return StreamingResponse(
                file_generator(),
                media_type=content_type,
                headers={
                    "Content-Disposition": f"inline; filename={filename}",
                    "Cache-Control": "no-cache",
                    "X-Conversation-ID": statement_data.get("conversation_id", ""),
                    "X-Case-Number": self._extract_case_number(statement_data) or ""
                }
            )
            
        except Exception as e:
            logger.error(f"Error streaming file content: {str(e)}")
            raise

    async def _get_file_metadata(self, file_url: str) -> Dict[str, Any]:
        """Get file metadata from Azure Blob Storage."""
        try:
            # Parse the blob URL
            parsed_url = urlparse(file_url)
            path_parts = parsed_url.path.strip('/').split('/')
            
            if len(path_parts) < 2:
                return {"size": None, "content_type": "application/pdf"}
            
            container_name = path_parts[0]
            blob_name = '/'.join(path_parts[1:])
            
            # Initialize blob service client
            blob_service_client = BlobServiceClient.from_connection_string(
                self.settings.AZURE_STORAGE_CONNECTION_STRING
            )
            
            # Get blob client
            blob_client = blob_service_client.get_blob_client(container_name, blob_name)
            
            # Get blob properties
            blob_properties = blob_client.get_blob_properties()
            
            return {
                "size": blob_properties.size,
                "content_type": blob_properties.content_settings.content_type or "application/pdf",
                "last_modified": blob_properties.last_modified,
                "etag": blob_properties.etag
            }
            
        except Exception as e:
            logger.error(f"Error getting file metadata: {str(e)}")
            return {"size": None, "content_type": "application/pdf"}

    async def _upload_file_to_blob(self, file_content: bytes, filename: str, conversation_id: str) -> str:
        """Upload file to Azure Blob Storage."""
        try:
            # Check if Azure Storage is configured
            if not self.settings.AZURE_STORAGE_CONNECTION_STRING:
                logger.warning("Azure Storage connection string not configured, using mock file URL")
                # Return a mock file URL when Azure Storage is not configured
                file_extension = filename.split('.')[-1] if '.' in filename else 'pdf'
                mock_blob_name = f"{conversation_id}/{uuid.uuid4()}.{file_extension}"
                return f"https://mock-storage.blob.core.windows.net/{self.settings.AZURE_STORAGE_CONTAINER_NAME}/{mock_blob_name}"
            
            # Initialize blob service client
            blob_service_client = BlobServiceClient.from_connection_string(
                self.settings.AZURE_STORAGE_CONNECTION_STRING
            )
            
            # Get container client
            container_client = blob_service_client.get_container_client(
                self.settings.AZURE_STORAGE_CONTAINER_NAME
            )
            
            # Create unique blob name
            file_extension = filename.split('.')[-1] if '.' in filename else 'pdf'
            blob_name = f"{conversation_id}/{uuid.uuid4()}.{file_extension}"
            
            # Upload file
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(file_content, overwrite=True)
            
            # Return blob URL
            return f"https://{self.settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{self.settings.AZURE_STORAGE_CONTAINER_NAME}/{blob_name}"
            
        except Exception as e:
            logger.error(f"Error uploading file to blob storage: {str(e)}")
            # Return a mock file URL as fallback
            file_extension = filename.split('.')[-1] if '.' in filename else 'pdf'
            mock_blob_name = f"{conversation_id}/{uuid.uuid4()}.{file_extension}"
            mock_url = f"https://mock-storage.blob.core.windows.net/{self.settings.AZURE_STORAGE_CONTAINER_NAME}/{mock_blob_name}"
            logger.info(f"Using mock file URL as fallback: {mock_url}")
            return mock_url

    async def _extract_document_data(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract text and structured data from uploaded document."""
        try:
            # For now, we'll use the actual data structure from page_extracted.json
            # In a real implementation, this would use OCR and AI to extract data
            extracted_data = {
                "document_id": "page",
                "document_type": "بيانات صحيفة الدعوى",
                "extracted_fields": [
                    {
                        "field_name": "case_number",
                        "field_name_arabic": "رقم الدعوى",
                        "field_value": "١٣٨٣٩٥١",
                        "confidence": 0.95,
                        "page_number": 1,
                        "bounding_box": None,
                        "field_type": "number",
                        "is_required": True,
                        "validation_rules": None
                    },
                    {
                        "field_name": "case_filing_date",
                        "field_name_arabic": "تاريخ رفع الدعوى",
                        "field_value": "١٤٤٤/٠٣/١٩",
                        "confidence": 0.95,
                        "page_number": 1,
                        "bounding_box": None,
                        "field_type": "date",
                        "is_required": True,
                        "validation_rules": None
                    },
                    {
                        "field_name": "plaintiff_name",
                        "field_name_arabic": "اسم المدعي",
                        "field_value": "عبير أحمد سعيد العمودي",
                        "confidence": 0.95,
                        "page_number": 1,
                        "bounding_box": None,
                        "field_type": "text",
                        "is_required": True,
                        "validation_rules": None
                    },
                    {
                        "field_name": "defendant_name",
                        "field_name_arabic": "اسم المدعى عليه",
                        "field_value": "أمانة منطقة الرياض",
                        "confidence": 0.95,
                        "page_number": 1,
                        "bounding_box": None,
                        "field_type": "text",
                        "is_required": True,
                        "validation_rules": None
                    },
                    {
                        "field_name": "case_type",
                        "field_name_arabic": "نوع الدعوى",
                        "field_value": "اعتراض على مخالفة تقديم الشيشة دون تصريح",
                        "confidence": 0.95,
                        "page_number": 1,
                        "bounding_box": None,
                        "field_type": "text",
                        "is_required": True,
                        "validation_rules": None
                    },
                    {
                        "field_name": "competent_court",
                        "field_name_arabic": "المحكمة المختصة",
                        "field_value": "المحكمة الإدارية بالرياض",
                        "confidence": 0.95,
                        "page_number": 1,
                        "bounding_box": None,
                        "field_type": "text",
                        "is_required": True,
                        "validation_rules": None
                    },
                    {
                        "field_name": "case_value",
                        "field_name_arabic": "قيمة الدعوى",
                        "field_value": "غير مذكورة",
                        "confidence": 0.85,
                        "page_number": 1,
                        "bounding_box": None,
                        "field_type": "text",
                        "is_required": False,
                        "validation_rules": None
                    },
                    {
                        "field_name": "case_subject",
                        "field_name_arabic": "موضوع الدعوى",
                        "field_value": "طلب إلغاء مخالفة رقم ١٠٠٠٠٠٠٣٦٥٧٨٤٦ بسبب تقديم الشيشة دون تصريح",
                        "confidence": 0.95,
                        "page_number": 1,
                        "bounding_box": None,
                        "field_type": "text",
                        "is_required": True,
                        "validation_rules": None
                    },
                    {
                        "field_name": "lawyer_name",
                        "field_name_arabic": "اسم المحامي",
                        "field_value": "غير مذكور",
                        "confidence": 0.85,
                        "page_number": 1,
                        "bounding_box": None,
                        "field_type": "text",
                        "is_required": False,
                        "validation_rules": None
                    },
                    {
                        "field_name": "phone_number",
                        "field_name_arabic": "رقم الهاتف",
                        "field_value": "٠٥٤٨٠٠٦٧٠٠",
                        "confidence": 0.95,
                        "page_number": 1,
                        "bounding_box": None,
                        "field_type": "phone",
                        "is_required": True,
                        "validation_rules": None
                    },
                    {
                        "field_name": "address",
                        "field_name_arabic": "العنوان",
                        "field_value": "رقم المبني ٢٩٧١، شارع سعيد بن عامر، وحدة رقم ١، الرياض، الرمز البريدي ١٢٣٩٥، الرمز الإضافي ٧١٧٤",
                        "confidence": 0.95,
                        "page_number": 1,
                        "bounding_box": None,
                        "field_type": "text",
                        "is_required": True,
                        "validation_rules": None
                    },
                    {
                        "field_name": "email",
                        "field_name_arabic": "البريد الإلكتروني",
                        "field_value": "maabeer@gmail.com",
                        "confidence": 0.95,
                        "page_number": 1,
                        "bounding_box": None,
                        "field_type": "email",
                        "is_required": False,
                        "validation_rules": None
                    },
                    {
                        "field_name": "commercial_registration_number",
                        "field_name_arabic": "رقم السجل التجاري",
                        "field_value": "١٠١٠٤٥٢٣٥٥",
                        "confidence": 0.95,
                        "page_number": 1,
                        "bounding_box": None,
                        "field_type": "number",
                        "is_required": False,
                        "validation_rules": None
                    },
                    {
                        "field_name": "violation_number",
                        "field_name_arabic": "رقم المخالفة",
                        "field_value": "١٠٠٠٠٠٠٣٦٥٧٨٤٦",
                        "confidence": 0.95,
                        "page_number": 1,
                        "bounding_box": None,
                        "field_type": "number",
                        "is_required": False,
                        "validation_rules": None
                    },
                    {
                        "field_name": "objection_number",
                        "field_name_arabic": "رقم التظلم",
                        "field_value": "٣٨٠٥٤٨٢",
                        "confidence": 0.95,
                        "page_number": 1,
                        "bounding_box": None,
                        "field_type": "number",
                        "is_required": False,
                        "validation_rules": None
                    }
                ],
                "validation_score": 0.75,
                "is_valid": False,
                "validation_errors": [
                    "عدم وضوح رقم الدعوى بشكل دقيق",
                    "عدم وجود تاريخ رفع الدعوى بشكل واضح ومحدد",
                    "عدم تحديد نوع الدعوى بشكل صريح"
                ],
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "total_pages": 3,
                "processing_status": "completed",
                "raw_text": "مُجُود ديوان المظَائِ أعلنـ 0 المحكمة الإدارية بالرياض تقارير نظام إدارة الدعاوى (٥٠٠٣) بيانات صحيفة الدعوى ١٤٤٤/٠٣/١٩ طلب جديد التاريخ بيانات المدعى : فرد الاسم عبير احمد سعيد العمودي المهنة بدون عمل مكان العمل بدون عمل الجنسية سعودي رقم السجل ١١١٠٢٢٥١٨٠ نوعه هوية وطنية مكان إقامة المدعي رقم المبني ٢٩٧١ الشارع سعيد بن عامر وحدة رقم ١ المدينة الرياض الرمز البريدي ١٢٣٩٥ الرمز الإضافي ٧١٧٤ البريد الإلكتروني maabeer@gmail.com الهاتف المتنقل ٠٥٤٨٠٠٦٧٠٠ بيانات المدعى عليه : جهة حكومية الاسم أمانة منطقة الرياض بيان اضافي مكان العمل الجنسية رقم السجل ٣٨٥ نوعه الموضوع : أنا صاحبة مقهئ وردة العرب لتقديم المشروبات (٤ اونس كافية ديزير)، سجل تجاري رقم ١٠١٠٤٥٢٣٥٥ وقائع الدعوى تمت زيارة مقر المقهى من قبل موظف أجادة التابع لأمانة منطقة الرياض وقام بإصدار مخالف رقم ١٠٠٠٠٠٠٣٦٥٧٨٤٦ وسبب المخالفة تقديم الشيشة دون تصريح وقد قمت برفع اعتراض على المخالف بمعاملة برقم ٣٨٠٥٤٨٢ ورفض الاعتراض من قبل جهة الإدارة نفسها وذلك غير صحيح على الاطلاق فأني يوجد لدي ترخيص تقديم منتجات التبغ وقد انتهت مدة الترخيص وهو من التراخيص التي ينتهي لانتهاء مدته ولم اقدم لاي عميل هذه المنتجات على الاطلاق مما الحق الضرر بي اطلب الغاء المخالف رقم ١٠٠٠٠٠٠٣٦٥٧٨٤٦ الاسانيد : هوية المدعية سجل التجاري صورة المخالفة صورة رفض الاعتراض رقم الاصدار ٢ تاريخ الاصدار ١٤٣٩ الصفحة : ١ من ٣ التاريخ : ١٤٤٤/٠٣/٢٠ ٢٣١٧٧٠٧ الكود المرجعي الوقت ٠١:٢٧ م مقدمة للمحكمة المحكمة الإدارية بالرياض رقم الطلب ١٣٨٣٩٥١ رقم قيد الدعوى"
            }
            
            logger.info(f"Extracted document data with {len(extracted_data['extracted_fields'])} fields")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting document data: {str(e)}")
            raise

    async def _validate_statement_of_claim(self, extracted_data: Dict[str, Any]) -> tuple[bool, float, List[str]]:
        """Validate extracted data against statement of claim requirements."""
        try:
            if extracted_data.get("document_type") != "بيانات صحيفة الدعوى":
                return False, 0.0, ["نوع المستند غير متوافق مع صحيفة الدعوى"]
            
            extracted_fields = extracted_data.get("extracted_fields", [])
            if not extracted_fields:
                return False, 0.0, ["لم يتم استخراج أي حقول من المستند"]
            
            required_fields = {
                "case_number": "رقم الدعوى",
                "case_filing_date": "تاريخ رفع الدعوى", 
                "plaintiff_name": "اسم المدعي",
                "defendant_name": "اسم المدعى عليه",
                "case_type": "نوع الدعوى",
                "competent_court": "المحكمة المختصة",
                "case_subject": "موضوع الدعوى",
                "phone_number": "رقم الهاتف",
                "address": "العنوان"
            }
            
            # Define optional fields
            optional_fields = {
                "case_value": "قيمة الدعوى",
                "lawyer_name": "اسم المحامي",
                "email": "البريد الإلكتروني",
                "commercial_registration_number": "رقم السجل التجاري",
                "violation_number": "رقم المخالفة",
                "objection_number": "رقم التظلم"
            }
            
            # Check for required fields
            missing_required_fields = []
            found_fields = {}
            
            for field in extracted_fields:
                field_name = field.get("field_name")
                if field_name:
                    found_fields[field_name] = field
            
            # Check required fields
            for field_name, arabic_name in required_fields.items():
                if field_name not in found_fields:
                    missing_required_fields.append(f"الحقل المطلوب مفقود: {arabic_name}")
                else:
                    field_data = found_fields[field_name]
                    # Check if field has a valid value
                    field_value = field_data.get("field_value", "").strip()
                    if not field_value or field_value in ["غير مذكور", "غير مذكورة", ""]:
                        missing_required_fields.append(f"قيمة الحقل فارغة: {arabic_name}")
            
            # Check field structure integrity
            structure_errors = []
            for field in extracted_fields:
                required_field_props = ["field_name", "field_name_arabic", "field_value", "confidence", "page_number", "field_type", "is_required"]
                for prop in required_field_props:
                    if prop not in field:
                        structure_errors.append(f"الحقل '{field.get('field_name', 'unknown')}' يفتقد إلى الخاصية: {prop}")
            
            # Calculate validation score
            total_required_fields = len(required_fields)
            found_required_fields = total_required_fields - len(missing_required_fields)
            base_score = found_required_fields / total_required_fields if total_required_fields > 0 else 0
            
            # Adjust score based on confidence levels
            confidence_sum = 0
            confidence_count = 0
            for field in extracted_fields:
                confidence = field.get("confidence", 0)
                if confidence > 0:
                    confidence_sum += confidence
                    confidence_count += 1
            
            avg_confidence = confidence_sum / confidence_count if confidence_count > 0 else 0
            final_score = (base_score * 0.7) + (avg_confidence * 0.3)
            
            # Determine if valid
            validation_errors = missing_required_fields + structure_errors
            is_valid = final_score > 0.7 and len(validation_errors) == 0
            
            # If there are validation errors from the original data, add them
            original_errors = extracted_data.get("validation_errors", [])
            if original_errors:
                validation_errors.extend(original_errors)
            
            logger.info(f"Validation completed - Score: {final_score:.2f}, Valid: {is_valid}, Errors: {len(validation_errors)}")
            
            return is_valid, final_score, validation_errors
            
        except Exception as e:
            logger.error(f"Error validating statement of claim: {str(e)}")
            return False, 0.0, [f"خطأ في التحقق من صحة المستند: {str(e)}"]

    def _extract_case_number(self, extracted_data: Dict[str, Any]) -> Optional[str]:
        """Extract case number from extracted fields."""
        try:
            for field in extracted_data.get("extracted_fields", []):
                if field.get("field_name") == "case_number":
                    return field.get("field_value")
            return None
        except Exception as e:
            logger.error(f"Error extracting case number: {str(e)}")
            return None

    async def _store_statement_of_claim(self, conversation_id: str, file_url: str, extracted_data: Dict[str, Any]):
        """Store statement of claim data in database."""
        try:
            statement_data = {
                "conversation_id": conversation_id,
                "file_url": file_url,
                **extracted_data,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Store in statement_of_claim collection
            await self.db.statement_of_claim.insert_one(statement_data)
            logger.info(f"Stored statement of claim for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error storing statement of claim: {str(e)}")
            raise

    async def _store_file_upload_message(self, filename: str, conversation_id: str, user_id: str):
        """Store user message about file upload."""
        try:
            file_message = MessageCreate(
                conversation_id=conversation_id,
                user_id=user_id,
                message_data={
                    "type": "user_message",
                    "query_type": "file",
                    "content": f"تم رفع الملف: {filename}",
                    "metadata": {
                        "filename": filename,
                        "upload_timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
            await self.message_service.create_message(file_message)
            logger.info(f"Stored file upload message for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error storing file upload message: {str(e)}")
            raise

    def _extract_field_value(self, extracted_data: Dict[str, Any], field_name: str, arabic_field_name: str) -> str:
        """Extract field value from extracted_data by field name or Arabic field name."""
        try:
            extracted_fields = extracted_data.get("extracted_fields", [])
            
            # First try to find by English field name
            for field in extracted_fields:
                if field.get("field_name") == field_name:
                    value = field.get("field_value", "")
                    if value and value not in ["غير مذكور", "unselected", ":unselected:"]:
                        return value
            
            # If not found, try by Arabic field name
            for field in extracted_fields:
                if field.get("field_name_arabic") == arabic_field_name:
                    value = field.get("field_value", "")
                    if value and value not in ["غير مذكور", "unselected", ":unselected:"]:
                        return value
            
            # Return default if not found
            return "غير مذكور"
            
        except Exception as e:
            logger.error(f"Error extracting field value for {field_name}: {str(e)}")
            return "غير مذكور"

    async def _generate_file_processing_response(self, is_valid: bool, case_number: Optional[str], validation_errors: List[str], conversation_id: str, extracted_data: Dict[str, Any]) -> str:
        """Generate Arabic response message for file processing result."""
        try:
            if is_valid and case_number:
                # Extract case details from extracted_data
                case_subject = self._extract_field_value(extracted_data, "case_subject", "موضوع الدعوى")
                case_type = self._extract_field_value(extracted_data, "case_type", "نوع الدعوى")
                plaintiff_name = self._extract_field_value(extracted_data, "plaintiff_name", "اسم المدعي")
                defendant_name = self._extract_field_value(extracted_data, "defendant_name", "اسم المدعى عليه")
                
                # Build detailed response
                response = f"""تم فحص الملف بنجاح ✅

رقم الدعوى: {case_number}

تفاصيل القضية:
• موضوع الدعوى: {case_subject}
• نوع الدعوى: {case_type}
• المدعي: {plaintiff_name}
• المدعى عليه: {defendant_name}

تم التحقق من صحة المستند وتخزينه في النظام. المستند متوافق مع متطلبات صحيفة الدعوى.

هل لديك مرفقات (مرفقات) إضافية تريد رفعها لإضافتها إلى ملف الدعوى؟"""
            else:
                error_details = "\n".join([f"• {error}" for error in validation_errors])
                response = f"""عذراً، الملف غير متوافق ❌

لا يمكن اعتبار هذا الملف كصحيفة دعوى صحيحة. يرجى التأكد من:

{error_details}

يرجى رفع ملف متوافق مع متطلبات صحيفة الدعوى."""
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating file processing response: {str(e)}")
            return "عذراً، حدث خطأ أثناء معالجة الملف. يرجى المحاولة مرة أخرى."

    async def _store_user_message(self, query: str, conversation_id: str, user_id: str = None) -> None:
        """Store the user's message in the database."""
        user_message = MessageCreate(
            conversation_id=conversation_id,
            user_id=user_id,
            message_data={
                "type": "user_message",
                "content": query,
                "metadata": {"query_length": len(query)}
            }
        )
        await self.message_service.create_message(user_message)
        logger.info(f"Stored user message for conversation {conversation_id}")

    async def _get_conversation_history(self, conversation_id: str) -> List[Dict]:
        """Retrieve conversation history from the database."""
        conversation_history = await self.message_service.get_full_conversation_history(conversation_id)
        
        if conversation_history:
            logger.info(f"Retrieved {len(conversation_history)} messages from conversation history")
        else:
            logger.info("No conversation history found")
            conversation_history = []
            
        return conversation_history

    def _extract_response_data(self, supervisor_result: Dict) -> tuple[str, Dict]:
        """Extract response content and metadata from supervisor result."""
        response_data = supervisor_result.get("response", {})
        
        # Initialize defaults
        content = "No response available"
        metadata = {}
        
        if isinstance(response_data, dict):
            if "content" in response_data:
                # Standard format from supervisor: {"content": "...", "metadata": {...}}
                content = response_data["content"]
                metadata = response_data.get("metadata", {})
            else:
                # Fallback for unexpected format
                content = str(response_data)
                logger.warning(f"Unexpected response_data format: {response_data}")
        elif isinstance(response_data, str):
            # If somehow it's still a string
            content = response_data
        else:
            # Final fallback
            content = str(response_data)
            logger.warning(f"Unexpected response_data type: {type(response_data)}")
        
        # Ensure content is always a string
        if not isinstance(content, str):
            logger.warning(f"Content is not a string, converting: {type(content)} -> {content}")
            content = str(content)
        
        logger.info(f"Extracted response content ({len(content)} chars)")
        if metadata:
            logger.info(f"Extracted metadata: {list(metadata.keys())}")
            
        return content, metadata

    async def _store_agent_message(self, content: str, agent_metadata: Dict, conversation_id: str, supervisor_result: Dict = None) -> None:
        """Store the agent's response in the database."""
        # Build complete metadata for storage including all available information
        storage_metadata = {
            "type": "agent_response",
            **agent_metadata  # Include search_method, original_query, etc.
        }
        
        # Add supervisor metadata if available
        if supervisor_result:
            storage_metadata["agent_type"] = supervisor_result.get("agent_type")
            storage_metadata["prompt_type"] = supervisor_result.get("prompt_type")
            storage_metadata["confidence"] = supervisor_result.get("confidence")
            storage_metadata["reasoning"] = supervisor_result.get("reasoning")
        
        agent_message = MessageCreate(
            conversation_id=conversation_id,
            user_id=None,
            message_data={
                "type": "agent_response", 
                "content": content,
                "metadata": storage_metadata
            }
        )
        await self.message_service.create_message(agent_message)
        
        # Log what we're storing for verification
        logger.info(f"Stored agent message with metadata: {list(storage_metadata.keys())}")
        
        logger.info(f"Stored agent response for conversation {conversation_id}")

    def _build_api_response(self, content: str, supervisor_result: Dict, agent_metadata: Dict) -> QueryResponse:
        """Build the final API response with metadata."""
        
        # Ensure content is a string (defensive programming)
        if not isinstance(content, str):
            logger.error(f"Content is not a string in _build_api_response: {type(content)} -> {content}")
            content = str(content)
        
        # Combine supervisor metadata with agent-specific metadata
        api_metadata = {
            "agent_type": supervisor_result.get("agent_type", "unknown"),
            "prompt_type": supervisor_result.get("prompt_type", "general"),
            "confidence": supervisor_result.get("confidence", 0.0),
            **agent_metadata  # Include search_method, original_query, etc.
        }
        
        # Only include these if they exist and are useful
        if supervisor_result.get("error"):
            api_metadata["error"] = supervisor_result["error"]
        if supervisor_result.get("reasoning"):
            api_metadata["reasoning"] = supervisor_result["reasoning"]
            
        return QueryResponse(response=content, metadata=api_metadata) 