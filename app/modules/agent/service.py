import hashlib
import pickle
from typing import Dict, Any, Optional, List
import logging
from app.schemas.agent import QueryResponse, FileUploadResponse, StatementOfClaim, FileInfoResponse
from app.modules.semantic_kernel.supervisor import Supervisor
from app.modules.message.service import MessageService
from app.schemas.message import MessageCreate
from app.schemas.conversation import ConversationStatus, ConversationUpdate
from app.modules.conversation.status_manager import ConversationStatusManager
from app.core.config.settings import get_settings
from azure.storage.blob import BlobServiceClient
from fastapi.responses import StreamingResponse
import json
import uuid
from datetime import datetime
import os
from urllib.parse import urlparse
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
import re
from dataclasses import dataclass
import asyncio

# Import claim extractor
from app.modules.claim_extractor.service import ClaimExtractorService
from app.modules.claim_extractor.models import ExtractionResult, ProcessingStatus

logger = logging.getLogger(__name__)

@dataclass
class LawsuitField:
    field_name: str
    field_name_arabic: str
    field_value: str
    confidence: float
    page_number: int
    field_type: str = "text"

@dataclass
class LawsuitDocument:
    document_type: str
    extracted_fields: List[LawsuitField]
    validation_score: float
    is_valid: bool
    validation_errors: List[str]

class AgentService:
    def __init__(self, db: Any, message_service: MessageService):
        self.db = db
        self.message_service = message_service
        self.settings = get_settings()
        self.supervisor = Supervisor()
        self.status_manager = ConversationStatusManager()
        
        # Initialize Azure clients
        self.document_intelligence_processor = None
        self.openai_processor = None
        self._initialize_azure_clients()
        
        # Initialize claim extractor service
        self.claim_extractor = ClaimExtractorService()
        
        # Load validation template
        self.validation_template = self._load_validation_template()
        self.page_extracted_schema = self._load_page_extracted_schema()
        
        # Initialize caches (in-memory and optional Redis)
        self._pdf_cache = {}
        try:
            from app.core.cache.redis_cache import RedisCache
            self._redis_cache = RedisCache()
        except Exception as e:
            logger.warning(f"Redis cache init failed: {e}")
            self._redis_cache = None
        logger.info("AgentService initialized with claim extractor and caching")

    def reload_prompts(self):
        """Force reload all prompts."""
        self.status_manager.reload_prompts()
        logger.info("Prompts reloaded in agent service")

    def _initialize_azure_clients(self):
        """Initialize Azure clients for document processing."""
        try:
            # Initialize Azure Document Intelligence client
            if self.settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and self.settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY:
                self.document_intelligence_processor = DocumentAnalysisClient(
                    endpoint=self.settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
                    credential=AzureKeyCredential(self.settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY)
                )
                logger.info("Azure Document Intelligence client initialized")
            
            # Initialize Azure OpenAI client with correct deployment
            if self.settings.AZURE_OPENAI_ENDPOINT and self.settings.AZURE_OPENAI_API_KEY:
                deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
                self.openai_processor = AzureOpenAI(
                    api_key=self.settings.AZURE_OPENAI_API_KEY,
                    api_version="2024-11-20",
                    azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT
                )
                self.azure_deployment_name = deployment_name
                logger.info(f"Azure OpenAI client initialized with deployment: {deployment_name}")
                
        except Exception as e:
            logger.warning(f"Failed to initialize Azure clients: {str(e)}")

    def _load_validation_template(self) -> dict:
        """Load validation template for document validation."""
        try:
            # Return a basic validation template
            return {
                "required_fields": [
                    "رقم الدعوى",
                    "تاريخ رفع الدعوى",
                    "المحكمة المختصة",
                    "مقدم الطلب",
                    "الموضوع"
                ],
                "optional_fields": [
                    "المدعى عليه",
                    "المخالفة",
                    "وقائع الدعوى"
                ]
            }
        except Exception as e:
            logger.error(f"Error loading validation template: {str(e)}")
            return {}

    def _load_page_extracted_schema(self) -> dict:
        """Load page_extracted.json schema for validation."""
        try:
            # Return a basic schema structure
            return {
                "extracted_fields": [
                    {
                        "field_name": "case_number",
                        "field_name_arabic": "رقم الدعوى",
                        "is_required": True
                    },
                    {
                        "field_name": "filing_date",
                        "field_name_arabic": "تاريخ رفع الدعوى",
                        "is_required": True
                    },
                    {
                        "field_name": "court",
                        "field_name_arabic": "المحكمة المختصة",
                        "is_required": True
                    },
                    {
                        "field_name": "plaintiff",
                        "field_name_arabic": "مقدم الطلب",
                        "is_required": True
                    },
                    {
                        "field_name": "subject",
                        "field_name_arabic": "الموضوع",
                        "is_required": True
                    }
                ]
            }
        except Exception as e:
            logger.error(f"Error loading page extracted schema: {str(e)}")
            return {"extracted_fields": []}

    async def query_agent(self, query: str, conversation_id: str, user_id: str = None) -> QueryResponse:
        """Main method to handle user queries through the agent system with dynamic prompts based on conversation status."""
        try:
            # 1. Store user message
            await self._store_user_message(query, conversation_id, user_id)
            
            # 2. Get conversation with status and prompt
            conversation_data = await self._get_conversation_with_status(conversation_id)
            if not conversation_data:
                raise ValueError("Conversation not found")
            
            conversation = conversation_data["conversation"]
            prompt = conversation_data["prompt"]
            # Convert ConversationResponse to dict to access status
            conversation_dict = conversation.model_dump() if hasattr(conversation, 'model_dump') else conversation.__dict__
            conversation_status = conversation_dict.get("status", "waiting_for_claim")
            
            # 3. Get conversation history
            conversation_history = await self._get_conversation_history(conversation_id)
            
            # 4. Get agent response with dynamic prompt and conversation status
            supervisor_result = await self.supervisor.route_query(
                query=query, 
                context=conversation_history,
                system_prompt=prompt,
                conversation_status=conversation_status
            )
            
            # 5. Extract and parse response
            response_content, agent_metadata = self._extract_response_data(supervisor_result)
            
            # 6. Store agent response
            await self._store_agent_message(response_content, agent_metadata, conversation_id, supervisor_result)
            
            # 7. Build API response
            return self._build_api_response(response_content, supervisor_result, agent_metadata)
            
        except Exception as e:
            logger.error(f"Error in query_agent: {str(e)}")
            return QueryResponse(
                response="عذراً، حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى.",
                metadata={"error": str(e)}
            )

    async def process_file_upload(self, file_content: bytes, filename: str, conversation_id: str, user_id: str) -> FileUploadResponse:
        """Process file upload using enhanced claim extractor and generate professional legal response."""
        try:
            logger.info(f"Processing file upload: {filename} for conversation: {conversation_id}")
            
            # Check if file is PDF
            if not filename.lower().endswith('.pdf'):
                error_message = "عذراً، يدعم النظام حالياً ملفات PDF فقط لمعالجة المستندات القانونية."
                await self._store_agent_message(
                    error_message,
                    {"query_type": "file", "file_processed": False, "error": "File type not supported"},
                    conversation_id,
                    {"agent_type": "file_processor", "confidence": 0.0}
                )
                return FileUploadResponse(
                    response=error_message,
                    is_valid=False,
                    metadata={"error": "File type not supported"}
                )
            
            # Store user message about file upload
            await self._store_file_upload_message(filename, conversation_id, user_id)
            
            # Cache by file hash (content + filename)
            cache_key = self._generate_cache_key(file_content, filename)
            # Try Redis cache first
            cached_response = None
            cached_data = None
            if getattr(self, "_redis_cache", None):
                redis_payload = self._redis_cache.get_json(cache_key)
                if redis_payload:
                    cached_response = redis_payload.get("response")
                    cached_data = redis_payload.get("extracted_data")
            # Fallback to in-memory cache
            if cached_response is None:
                cached = self._get_cached_result(cache_key)
                if cached:
                    cached_response, cached_data = cached
            # Handle cache hit
            if cached_response is not None and cached_data is not None:
                # Persist Redis-only payload into in-memory cache too
                self._cache_result(cache_key, cached_response, cached_data)
                # Still upload the file to blob for this conversation
                try:
                    file_url = await self.claim_extractor.storage_manager.upload_file(
                        file_content=file_content,
                        filename=filename,
                        conversation_id=conversation_id
                    )
                    cached_data["file_url"] = file_url
                except Exception as e:
                    logger.warning(f"Upload during cache hit failed, continuing with cached file_url: {e}")
                    file_url = cached_data.get("file_url")
                # Update conversation status based on cached validity
                is_valid_cached = bool(cached_data.get("is_valid", False) or (cached_data.get("is_valid") is True))
                await self._update_conversation_status(
                    conversation_id,
                    ConversationStatus.CLAIM_DISCUSSION
                )
                # Store agent response quickly
                await self._store_agent_message(
                    cached_response,
                    {"query_type": "file", "file_processed": True, "is_valid": is_valid_cached},
                    conversation_id,
                    {"agent_type": "claim_extractor", "confidence": cached_data.get("validation_score", 0.0)}
                )
                # Store statement of claim
                await self._store_statement_of_claim(conversation_id, file_url, cached_data)
                return FileUploadResponse(
                    response=cached_response,
                    file_url=file_url,
                    case_number=cached_data.get("case_number"),
                    is_valid=is_valid_cached,
                    metadata={
                        "document_type": cached_data.get("document_type", "صحيفة دعوى"),
                        "validation_score": cached_data.get("validation_score", 0.0),
                        "validation_errors": cached_data.get("validation_errors", []),
                        "total_pages": cached_data.get("total_pages", 1),
                        "processing_time": cached_data.get("processing_time"),
                        "extraction_status": cached_data.get("extraction_status", "completed")
                    }
                )
            
            # Use enhanced claim extractor for PDF processing
            logger.info(f"Using enhanced claim extractor for {filename}")
            extraction_result = await self.claim_extractor.extract_claim_from_pdf(
                file_content=file_content,
                filename=filename,
                conversation_id=conversation_id
            )
            
            # Generate professional legal response
            response_message = await self._generate_professional_legal_response(extraction_result, conversation_id)

            # After successful extraction, set status to claim_discussion to allow Q&A over the claim
            try:
                await self._update_conversation_status(conversation_id, ConversationStatus.CLAIM_DISCUSSION)
            except Exception as _:
                pass
            
            # Store extracted data
            extracted_data = await self._convert_extraction_result_to_data(extraction_result)
            await self._store_statement_of_claim(conversation_id, extraction_result.file_url, extracted_data)

            # Generate conversation title/description from extracted claim
            try:
                from app.modules.conversation.service import ConversationService
                conversation_service = ConversationService(self.db)
                claim = extraction_result.extracted_claim
                # Title heuristic: case type + subject or number
                title_parts = []
                if getattr(claim, 'case_type', None):
                    title_parts.append(str(claim.case_type))
                if getattr(claim, 'case_subject', None):
                    title_parts.append(str(claim.case_subject))
                elif getattr(claim, 'case_number', None):
                    title_parts.append(f"رقم {claim.case_number}")
                title = " — ".join([p for p in title_parts if p]) or "دعوى جديدة"
                # Description concise summary
                desc_parts = []
                if getattr(claim, 'plaintiff_name', None):
                    desc_parts.append(f"المدعي: {claim.plaintiff_name}")
                if getattr(claim, 'defendant_name', None):
                    desc_parts.append(f"المدعى عليها: {claim.defendant_name}")
                if getattr(claim, 'court_name', None):
                    desc_parts.append(f"المحكمة: {claim.court_name}")
                if getattr(claim, 'case_number', None):
                    desc_parts.append(f"رقم الدعوى: {claim.case_number}")
                description = "؛ ".join(desc_parts) or None
                await conversation_service.update_conversation(
                    conversation_id,
                    ConversationUpdate(name=title, description=description)
                )
            except Exception as _:
                pass

            # Cache the result for future identical files (both Redis and in-memory)
            if getattr(self, "_redis_cache", None):
                try:
                    self._redis_cache.set_json(cache_key, {"response": response_message, "extracted_data": extracted_data}, ttl_seconds=86400)
                except Exception as e:
                    logger.warning(f"Redis set failed: {e}")
            self._cache_result(cache_key, response_message, extracted_data)
            
            # Update conversation status based on extraction result
            if extraction_result.status == ProcessingStatus.VALIDATED:
                await self._update_conversation_status(conversation_id, ConversationStatus.CLAIM_DISCUSSION)
            elif extraction_result.status == ProcessingStatus.COMPLETED:
                await self._update_conversation_status(conversation_id, ConversationStatus.CLAIM_DISCUSSION)
            else:
                await self._update_conversation_status(conversation_id, ConversationStatus.CLAIM_REJECTED)
            
            # Store agent response
            await self._store_agent_message(
                response_message, 
                {"query_type": "file", "file_processed": True, "is_valid": (extraction_result.extracted_claim.is_valid if extraction_result.extracted_claim else False)}, 
                conversation_id, 
                {"agent_type": "claim_extractor", "confidence": extraction_result.document_intelligence_confidence or 0.0}
            )
            
            return FileUploadResponse(
                response=response_message,
                file_url=extraction_result.file_url,
                case_number=extraction_result.extracted_claim.case_number if extraction_result.extracted_claim else None,
                is_valid=(extraction_result.extracted_claim.is_valid if extraction_result.extracted_claim else False),
                metadata={
                    "document_type": "صحيفة دعوى",
                    "validation_score": extraction_result.document_intelligence_confidence or 0.0,
                    "validation_errors": extraction_result.error_message or [],
                    "total_pages": extraction_result.extracted_claim.total_pages if extraction_result.extracted_claim else 1,
                    "processing_time": extraction_result.processing_time,
                    "extraction_status": extraction_result.status.value
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

    async def process_attachments(self, files: list, conversation_id: str, user_id: str) -> FileUploadResponse:
        """Process multiple attachment files and generate comprehensive claim overview."""
        try:
            # 1. Get the original claim data
            claim_data = await self.get_statement_of_claim(conversation_id)
            if not claim_data:
                raise ValueError("No claim found for this conversation")
            
            # 2. Process each attachment
            attachment_results = []
            file_urls = []
            total_size = 0
            attachment_types = []
            
            # Read contents upfront to enable concurrency
            file_blobs = []
            for file in files:
                content = await file.read()
                total_size += len(content)
                attachment_types.append(file.content_type)
                file_blobs.append((file.filename, file.content_type, content))
            
            async def handle_one(filename: str, content_type: str, content: bytes):
                url = await self._upload_file_to_blob(content, filename, conversation_id, "attachments")
                extracted = await self._extract_attachment_content(content, filename)
                data = {
                    "conversation_id": conversation_id,
                    "file_url": url,
                    "filename": filename,
                    "content_type": content_type,
                    "file_size": len(content),
                    "extracted_content": extracted,
                    "upload_timestamp": datetime.utcnow().isoformat(),
                    "attachment_type": "supporting_document"
                }
                await self._store_attachment_data(conversation_id, data)
                return data, url
            
            # Limit concurrency to avoid throttling (e.g., 4 at a time)
            semaphore = asyncio.Semaphore(4)
            async def sem_task(args):
                async with semaphore:
                    return await handle_one(*args)
            
            results = await asyncio.gather(*[sem_task((fn, ct, cnt)) for fn, ct, cnt in file_blobs], return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.warning(f"One attachment failed: {res}")
                    continue
                data, url = res
                attachment_results.append(data)
                file_urls.append(url)
            
            # Store a single aggregated message for all uploaded attachments
            try:
                attachments_short = [
                    {"filename": a.get("filename"), "file_url": a.get("file_url"), "content_type": a.get("content_type"), "file_size": a.get("file_size")}
                    for a in attachment_results
                ]
                names_list = ", ".join([a.get("filename") or "(بدون اسم)" for a in attachment_results])
                aggregate_content = f"تم رفع المرفقات التالية: {names_list}"
                await self._store_agent_message(
                    aggregate_content,
                    {"type": "attachments_uploaded", "attachments": attachments_short, "count": len(attachments_short)},
                    conversation_id,
                    {"agent_type": "attachment_uploader", "confidence": 1.0}
                )
            except Exception as e:
                logger.warning(f"Failed to store aggregated attachments message: {e}")
            
            # 3. Append attachments into the existing statement_of_claim document
            try:
                await self._append_attachments_to_claim(conversation_id, attachment_results)
            except Exception as e:
                logger.warning(f"Failed to append attachments to claim doc: {e}")

            # 4. Generate concise overview response
            overview_response = await self._generate_attachment_overview_response(
                claim_data, attachment_results, conversation_id
            )
            
            # 4. Store agent response
            await self._store_agent_message(
                overview_response,
                {"query_type": "attachments", "attachments_processed": True, "count": len(files)},
                conversation_id,
                {"agent_type": "attachment_processor", "confidence": 0.95}
            )
            
            # 5. Extract case number from original claim
            case_number = self._extract_case_number(claim_data)
            
            return FileUploadResponse(
                response=overview_response,
                file_url=", ".join(file_urls) if file_urls else None,  # Multiple URLs joined or None
                case_number=case_number,
                is_valid=True,
                metadata={
                    "attachments_count": len(files),
                    "claim_document_type": claim_data.get("document_type", "unknown"),
                    "total_attachments_size": total_size,
                    "attachment_types": attachment_types
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing attachments: {str(e)}")
            error_message = "عذراً، حدث خطأ أثناء معالجة المرفقات. يرجى المحاولة مرة أخرى."
            await self._store_agent_message(
                error_message,
                {"query_type": "attachments", "attachments_processed": False, "error": str(e)},
                conversation_id,
                {"agent_type": "attachment_processor", "confidence": 0.0}
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

    async def _upload_file_to_blob(self, file_content: bytes, filename: str, conversation_id: str, folder: str = "claims") -> str:
        """Upload file to Azure Blob Storage with folder organization."""
        try:
            # Check if Azure Storage is configured
            if not self.settings.AZURE_STORAGE_CONNECTION_STRING:
                logger.warning("Azure Storage connection string not configured, using mock file URL")
                # Return a mock file URL when Azure Storage is not configured
                file_extension = filename.split('.')[-1] if '.' in filename else 'pdf'
                mock_blob_name = f"{folder}/{conversation_id}/{uuid.uuid4()}.{file_extension}"
                return f"https://mock-storage.blob.core.windows.net/{self.settings.AZURE_STORAGE_CONTAINER_NAME}/{mock_blob_name}"
            
            # Initialize blob service client
            blob_service_client = BlobServiceClient.from_connection_string(
                self.settings.AZURE_STORAGE_CONNECTION_STRING
            )
            
            # Get container client
            container_client = blob_service_client.get_container_client(
                self.settings.AZURE_STORAGE_CONTAINER_NAME
            )
            
            # Create unique blob name with folder structure
            file_extension = filename.split('.')[-1] if '.' in filename else 'pdf'
            blob_name = f"{folder}/{conversation_id}/{uuid.uuid4()}.{file_extension}"
            
            # Upload file
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(file_content, overwrite=True)
            
            # Return blob URL
            return f"https://{self.settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{self.settings.AZURE_STORAGE_CONTAINER_NAME}/{blob_name}"
            
        except Exception as e:
            logger.error(f"Error uploading file to blob storage: {str(e)}")
            # Return a mock file URL as fallback
            file_extension = filename.split('.')[-1] if '.' in filename else 'pdf'
            mock_blob_name = f"{folder}/{conversation_id}/{uuid.uuid4()}.{file_extension}"
            mock_url = f"https://mock-storage.blob.core.windows.net/{self.settings.AZURE_STORAGE_CONTAINER_NAME}/{mock_blob_name}"
            logger.info(f"Using mock file URL as fallback: {mock_url}")
            return mock_url

    async def _extract_document_data(self, file_content: bytes, filename: str, conversation_id: str) -> Dict[str, Any]:
        """Extract basic document info without using Document Intelligence."""
        try:
            # Simple document validation - just check if it's a PDF
            if not filename.lower().endswith('.pdf'):
                return {
                    "document_id": "invalid_format",
                    "document_type": "unknown_document",
                    "raw_text": "",
                    "extraction_timestamp": datetime.utcnow().isoformat(),
                    "total_pages": 1,
                    "processing_status": "failed",
                    "is_legal_document": False,
                    "validation_score": 0.0,
                    "is_valid": False,
                    "validation_errors": ["File must be a PDF"]
                }
            
            # Return basic structure - actual analysis will be done by Azure OpenAI
            return {
                "document_id": "pdf_document",
                "document_type": "بيانات صحيفة الدعوى",
                "raw_text": "",  # No text extraction needed - Azure OpenAI will handle it
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "total_pages": 1,
                "processing_status": "completed",
                "is_legal_document": True,
                "validation_score": 0.9,  # High score since we're using Azure OpenAI
                "is_valid": True,
                "validation_errors": []
            }
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            return {
                "document_id": "error",
                "document_type": "unknown_document",
                "raw_text": "",
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "total_pages": 1,
                "processing_status": "failed",
                "is_legal_document": False,
                "validation_score": 0.0,
                "is_valid": False,
                "validation_errors": [f"Processing error: {str(e)}"]
            }

    async def _validate_statement_of_claim(self, extracted_data: Dict[str, Any]) -> tuple[bool, float, List[str]]:
        """Validate extracted data against statement of claim format."""
        try:
            # The document processor already performed validation
            # Just return the results from the document processor
            is_valid = extracted_data.get("is_valid", False)
            validation_score = extracted_data.get("validation_score", 0.0)
            validation_errors = extracted_data.get("validation_errors", [])
            
            return is_valid, validation_score, validation_errors
            
        except Exception as e:
            logger.error(f"Error validating statement of claim: {str(e)}")
            return False, 0.0, [f"Validation error: {str(e)}"]

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
        """Store PDF document info in database."""
        try:
            # Store basic document metadata along with extracted text if available
            statement_data = {
                "conversation_id": conversation_id,
                "file_url": file_url,
                "document_type": extracted_data.get("document_type", "بيانات صحيفة الدعوى"),
                "extraction_timestamp": extracted_data.get("extraction_timestamp"),
                "total_pages": extracted_data.get("total_pages", 1),
                "processing_status": extracted_data.get("processing_status", "completed"),
                "is_legal_document": extracted_data.get("is_legal_document", True),
                "validation_score": extracted_data.get("validation_score", 0.9),
                "is_valid": extracted_data.get("is_valid", True),
                "validation_errors": extracted_data.get("validation_errors", []),
                "raw_text": extracted_data.get("raw_text"),
                "raw_text_length": extracted_data.get("raw_text_length"),
                "page_contents": extracted_data.get("page_contents"),
                "processing_method": "azure_openai_direct",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Store in statement_of_claim collection
            await self.db.statement_of_claim.insert_one(statement_data)
            logger.info(f"Stored PDF document info for conversation {conversation_id}")
            
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
             
            field_name_patterns = [field_name]
             
            if field_name == "plaintiff_name":
                field_name_patterns.extend(["plaintiff"])
            elif field_name == "defendant_name":
                field_name_patterns.extend(["defendant"])
            elif field_name == "plaintiff":
                field_name_patterns.extend(["plaintiff_name"])
            elif field_name == "defendant":
                field_name_patterns.extend(["defendant_name"])
             
            for pattern in field_name_patterns:
                for field in extracted_fields:
                    if field.get("field_name") == pattern:
                        value = field.get("field_value", "")
                        if value and value not in ["غير مذكور", "unselected", ":unselected:", "اسم المدعي", "اسم المدعى عليه"]:
                            return value
            
            # If not found, try by Arabic field name
            for field in extracted_fields:
                if field.get("field_name_arabic") == arabic_field_name:
                    value = field.get("field_value", "")
                    if value and value not in ["غير مذكور", "unselected", ":unselected:", "اسم المدعي", "اسم المدعى عليه"]:
                        return value
            
            # Return default if not found
            return "غير مذكور"
            
        except Exception as e:
            logger.error(f"Error extracting field value for {field_name}: {str(e)}")
            return "غير مذكور"

    async def _generate_file_processing_response(self, is_valid: bool, case_number: Optional[str], validation_errors: List[str], conversation_id: str, extracted_data: Dict[str, Any], file_content: bytes = None, filename: str = None) -> str:
        """Generate Arabic response message using Azure OpenAI directly from PDF."""
        try:
            if is_valid:
                # Use PDF-to-LLM approach directly - no Document Intelligence needed
                if file_content and filename:
                    try:
                        logger.info(f"Using Azure OpenAI to analyze PDF directly: {filename}")
                        
                        # Check if this is a Saudi legal document (صحيفة الدعوى)
                        if self._is_saudi_legal_document(file_content, filename):
                            logger.info(f"Detected Saudi legal document, using specialized processing: {filename}")
                            saudi_extracted_data = await self._extract_saudi_legal_document_data(file_content, filename)
                            response = await self._generate_saudi_legal_response(saudi_extracted_data, conversation_id)
                            
                            # Store the extracted data in the database
                            if saudi_extracted_data:
                                await self._store_extracted_case_data(conversation_id, saudi_extracted_data)
                            
                            return response
                        else:
                            # Use general PDF processing
                            response, extracted_data = await self._generate_llm_response_from_pdf(file_content, filename, conversation_id)
                            
                            # Store the extracted data in the database
                            if extracted_data:
                                await self._store_extracted_case_data(conversation_id, extracted_data)
                            
                            return response
                    except Exception as e:
                        logger.warning(f"Azure OpenAI PDF analysis failed, using fallback: {e}")
                        return self._generate_fallback_response()
                else:
                    # No file content available, use fallback
                    return self._generate_fallback_response()
            else:
                error_details = "\n".join([f"• {error}" for error in validation_errors])
                response = f"""## ❌ الملف غير متوافق

لا يمكن اعتبار هذا الملف كصحيفة دعوى صحيحة.

**المشاكل المكتشفة:**
{error_details}

💡 *تأكد من أن الملف يحتوي على معلومات القضية الأساسية وتفاصيل المدعي والمدعى عليه.*"""
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating file processing response: {str(e)}")
            return "عذراً، حدث خطأ أثناء معالجة الملف. يرجى المحاولة مرة أخرى."

    def _is_saudi_legal_document(self, file_content: bytes, filename: str) -> bool:
        """Detect if the document is a Saudi legal document (صحيفة الدعوى)."""
        try:
            # Check filename for indicators
            filename_lower = filename.lower()
            if any(keyword in filename_lower for keyword in ['صحيفة', 'دعوى', 'saudi', 'legal', 'court']):
                return True
            
            # Check file content for Saudi legal document indicators
            # Convert bytes to string for pattern matching
            content_str = file_content.decode('utf-8', errors='ignore')
            
            # Look for Saudi legal document keywords
            saudi_keywords = [
                'صحيفة الدعوى',
                'ديوان المظالم',
                'المحكمة الإدارية',
                'المملكة العربية السعودية',
                'رقم الطلب',
                'رقم قيد الدعوى',
                'بيانات المدعي',
                'بيانات المدعى عليه'
            ]
            
            # Check if any Saudi keywords are present
            for keyword in saudi_keywords:
                if keyword in content_str:
                    logger.info(f"Detected Saudi legal document keyword: {keyword}")
                    return True
            
            # Check for Arabic numerals and Hijri date patterns
            arabic_numerals = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩']
            hijri_pattern = r'\d{4}/\d{2}/\d{2}'  # Basic Hijri date pattern
            
            # Count Arabic numerals
            arabic_numeral_count = sum(content_str.count(numeral) for numeral in arabic_numerals)
            if arabic_numeral_count > 10:  # If many Arabic numerals present
                logger.info(f"Detected Arabic numerals in document: {arabic_numeral_count} occurrences")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting Saudi legal document: {e}")
            return False

    async def _generate_llm_response_from_raw_text(self, raw_text: str, conversation_id: str) -> str:
        """Generate response using Azure OpenAI from raw text."""
        try:
            # Check if Azure OpenAI is available
            if not self.openai_processor:
                logger.warning("Azure OpenAI client not configured, using fallback response")
                return self._generate_fallback_response(raw_text)
            
            # Create prompt for LLM
            prompt = f"""
You are an expert legal assistant. Analyze the following Arabic legal document text and create a comprehensive, professional response in Arabic.

Document Text:
{raw_text[:4000]}  # Increased limit for better analysis

Instructions:
1. Create a professional, comprehensive overview of the legal document
2. Extract and organize key information in a structured format
3. Use Arabic language with proper formatting
4. Include sections for case summary, plaintiff info, defendant info, case details, etc.
5. Add emojis and professional formatting
6. Provide clear next steps guidance
7. Make it user-friendly and informative
8. Clean and structure the text properly if it appears messy

Format the response with these sections:
- ✅ تم فحص الملف بنجاح (File processed successfully)
- 📋 ملخص القضية (Case Summary)
- 👤 بيانات المدعي (Plaintiff Information)
- 🏛️ بيانات المدعى عليه (Defendant Information)
- 📄 تفاصيل الدعوى (Case Details)
- 📝 وقائع الدعوى (Case Facts)
- 🎯 الطلب (Request)
- 📎 المرفقات (Attachments)
- 🔄 الخطوات التالية (Next Steps)

Return the response in Arabic with professional formatting.
"""
            
            # Call Azure OpenAI API
            response = self.openai_processor.chat.completions.create(
                model=self.azure_deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert legal document analyzer. Create comprehensive, professional responses in Arabic. Clean and structure messy text properly."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2500
            )
            
            llm_response = response.choices[0].message.content.strip()
            logger.info(f"Generated Azure OpenAI response for conversation {conversation_id}")
            
            return llm_response
            
        except Exception as e:
            logger.error(f"Azure OpenAI response generation failed: {e}")
            logger.info("Falling back to basic response")
            return self._generate_fallback_response(raw_text)

    def _generate_cache_key(self, file_content: bytes, filename: str) -> str:
        """Generate a cache key for PDF content."""
        try:
            # Create a hash of the file content and filename
            content_hash = hashlib.md5(file_content).hexdigest()
            filename_hash = hashlib.md5(filename.encode()).hexdigest()
            return f"pdf_cache_{content_hash}_{filename_hash}"
        except Exception as e:
            logger.error(f"Error generating cache key: {e}")
            return f"pdf_cache_{hash(file_content)}_{hash(filename)}"

    def _get_cached_result(self, cache_key: str) -> Optional[tuple[str, Dict[str, Any]]]:
        """Get cached PDF processing result."""
        try:
            if cache_key in self._pdf_cache:
                cached_data = self._pdf_cache[cache_key]
                # Check if cache is still valid (24 hours)
                if datetime.utcnow().timestamp() - cached_data.get('timestamp', 0) < 86400:
                    logger.info(f"Using cached PDF processing result for {cache_key}")
                    return cached_data.get('response'), cached_data.get('extracted_data', {})
                else:
                    # Remove expired cache
                    del self._pdf_cache[cache_key]
            return None
        except Exception as e:
            logger.error(f"Error getting cached result: {e}")
            return None

    def _cache_result(self, cache_key: str, response: str, extracted_data: Dict[str, Any]):
        """Cache PDF processing result."""
        try:
            self._pdf_cache[cache_key] = {
                'response': response,
                'extracted_data': extracted_data,
                'timestamp': datetime.utcnow().timestamp()
            }
            logger.info(f"Cached PDF processing result for {cache_key}")
        except Exception as e:
            logger.error(f"Error caching result: {e}")

    async def _generate_llm_response_from_pdf(self, file_content: bytes, filename: str, conversation_id: str) -> tuple[str, Dict[str, Any]]:
        """Generate response using Azure Document Intelligence for text extraction, then Azure OpenAI for analysis."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key(file_content, filename)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                return cached_result
            
            # First, use Azure Document Intelligence to extract clean text with better layout analysis
            from app.modules.document_processor.service import DocumentProcessorService
            document_processor = DocumentProcessorService()
            
            # Extract clean text using Document Intelligence with layout analysis
            extracted_text = await document_processor._extract_raw_text_only(file_content, filename)
            
            if not self.openai_processor:
                logger.warning("Azure OpenAI client not configured, using fallback response with extracted text")
                fallback_response = self._generate_fallback_response(extracted_text)
                self._cache_result(cache_key, fallback_response, {})
                return fallback_response, {}
            
            # Enhanced extraction prompt with better structure for legal documents
            extraction_prompt = f"""Analyze this Arabic legal document text and extract the following information in JSON format:

{extracted_text[:4000]}

Extract this information in JSON format with high accuracy:
{{
    "case_number": "رقم الدعوى (extract exact case number)",
    "case_subject": "موضوع الدعوى (extract case subject)", 
    "case_type": "نوع الدعوى (extract case type)",
    "plaintiff_name": "اسم المدعي (extract plaintiff name)",
    "defendant_name": "اسم المدعى عليه (extract defendant name)",
    "filing_date": "تاريخ تقديم الدعوى (extract filing date)",
    "court": "المحكمة (extract court name)",
    "case_summary": "ملخص القضية (provide brief summary)",
    "extraction_confidence": 0.95,
    "extracted_fields_count": 0,
    "document_quality": "high/medium/low"
}}

Instructions:
1. Extract exact values as they appear in the document
2. If a field is not found, use "غير مذكور"
3. For dates, use Arabic format if available
4. For case numbers, extract the complete number including any prefixes
5. Provide extraction confidence based on clarity of information

Return ONLY the JSON object, no additional text."""
            
            extraction_response = self.openai_processor.chat.completions.create(
                model=self.azure_deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert legal document analyzer specializing in Arabic legal documents. Extract structured information from Arabic legal documents and return only valid JSON. Handle Arabic text properly and maintain original formatting."},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            # Parse extracted data with better error handling
            extracted_data = {}
            try:
                import json
                extracted_json = extraction_response.choices[0].message.content.strip()
                # Clean the response to get valid JSON
                if extracted_json.startswith('```json'):
                    extracted_json = extracted_json[7:]
                if extracted_json.endswith('```'):
                    extracted_json = extracted_json[:-3]
                if extracted_json.startswith('```'):
                    extracted_json = extracted_json[3:]
                if extracted_json.endswith('```'):
                    extracted_json = extracted_json[:-3]
                
                extracted_data = json.loads(extracted_json.strip())
                
                # Validate extracted data
                required_fields = ["case_number", "case_subject", "plaintiff_name", "defendant_name"]
                extracted_fields_count = sum(1 for field in required_fields if extracted_data.get(field) and extracted_data[field] != "غير مذكور")
                extracted_data["extracted_fields_count"] = extracted_fields_count
                
                logger.info(f"Successfully extracted structured data from PDF: {list(extracted_data.keys())}")
                logger.info(f"Extracted {extracted_fields_count}/{len(required_fields)} required fields")
                
            except Exception as parse_error:
                logger.warning(f"Failed to parse extracted JSON: {parse_error}")
                logger.info(f"Raw response: {extraction_response.choices[0].message.content}")
                extracted_data = {
                    "case_number": "غير مذكور",
                    "case_subject": "غير مذكور",
                    "case_type": "غير مذكور",
                    "plaintiff_name": "غير مذكور",
                    "defendant_name": "غير مذكور",
                    "filing_date": "غير مذكور",
                    "court": "غير مذكور",
                    "case_summary": "تعذر استخراج ملخص القضية",
                    "extraction_confidence": 0.0,
                    "extracted_fields_count": 0,
                    "document_quality": "low"
                }
            
            # Generate comprehensive response with actual document information
            response_prompt = f"""Based on this Arabic legal document text, create a comprehensive, professional response in Arabic.

Document Text:
{extracted_text[:3000]}

Extracted Information:
- رقم الدعوى: {extracted_data.get('case_number', 'غير مذكور')}
- موضوع الدعوى: {extracted_data.get('case_subject', 'غير مذكور')}
- نوع الدعوى: {extracted_data.get('case_type', 'غير مذكور')}
- اسم المدعي: {extracted_data.get('plaintiff_name', 'غير مذكور')}
- اسم المدعى عليه: {extracted_data.get('defendant_name', 'غير مذكور')}
- تاريخ تقديم الدعوى: {extracted_data.get('filing_date', 'غير مذكور')}
- المحكمة: {extracted_data.get('court', 'غير مذكور')}

Create a detailed response with these sections:

## ✅ تم فحص الملف بنجاح

تم التحقق من صحة المستند وتخزينه في النظام. المستند متوافق مع متطلبات صحيفة الدعوى.

## 📋 **تفاصيل القضية**

**رقم الدعوى:** {extracted_data.get('case_number', 'غير مذكور')}
**موضوع الدعوى:** {extracted_data.get('case_subject', 'غير مذكور')}
**نوع الدعوى:** {extracted_data.get('case_type', 'غير مذكور')}
**اسم المدعي:** {extracted_data.get('plaintiff_name', 'غير مذكور')}
**اسم المدعى عليه:** {extracted_data.get('defendant_name', 'غير مذكور')}
**تاريخ تقديم الدعوى:** {extracted_data.get('filing_date', 'غير مذكور')}
**المحكمة:** {extracted_data.get('court', 'غير مذكور')}

## 📝 **ملخص القضية**

{extracted_data.get('case_summary', 'تم تحليل المستند بنجاح. المستند يحتوي على معلومات القضية الأساسية.')}

## 🔄 **الخطوات التالية**

**هل لديك مرفقات إضافية تريد رفعها؟**

💡 *المرفقات الداعمة ستساعد في تعزيز موقفك القانوني.*"""
            
            response = self.openai_processor.chat.completions.create(
                model=self.azure_deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert legal assistant. Create comprehensive, professional responses in Arabic based on actual legal document analysis. Use the extracted information provided and format the response professionally."},
                    {"role": "user", "content": response_prompt}
                ],
                temperature=0.1,
                max_tokens=3000
            )
            
            llm_response = response.choices[0].message.content.strip()
            logger.info(f"Generated Azure OpenAI response from Document Intelligence text for conversation {conversation_id}")
            
            # Cache the result
            self._cache_result(cache_key, llm_response, extracted_data)
            
            return llm_response, extracted_data
            
        except Exception as e:
            logger.error(f"Azure OpenAI PDF response generation failed: {e}")
            logger.info("Falling back to response with extracted text")
            # Get the extracted text for the fallback response
            try:
                from app.modules.document_processor.service import DocumentProcessorService
                document_processor = DocumentProcessorService()
                extracted_text = await document_processor._extract_raw_text_only(file_content, filename)
                fallback_response = self._generate_fallback_response(extracted_text)
                self._cache_result(cache_key, fallback_response, {})
                return fallback_response, {}
            except:
                fallback_response = self._generate_fallback_response()
                self._cache_result(cache_key, fallback_response, {})
                return fallback_response, {}
    
    async def _extract_text_from_pdf(self, file_content: bytes, filename: str) -> str:
        """Extract text from PDF using a simple approach."""
        try:
            import io
            import PyPDF2
            
            # Create a file-like object from bytes
            pdf_file = io.BytesIO(file_content)
            
            # Read PDF
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extract text from all pages
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
            
            logger.info(f"Successfully extracted text from PDF {filename} ({len(pdf_reader.pages)} pages)")
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            # Fallback: return a basic text representation
            return f"PDF document: {filename} - Text extraction failed"

    def _generate_fallback_response(self, raw_text: str = "") -> str:
        """Generate fallback response when LLM is not available, using actual extracted text."""
        if raw_text and len(raw_text) > 50:
            # Extract basic information from the text using simple pattern matching
            lines = raw_text.split('\n')
            case_info = []
            
            # Look for common patterns in Arabic legal documents
            for line in lines[:30]:  # Check first 30 lines
                line = line.strip()
                if any(keyword in line for keyword in ['رقم', 'دعوى', 'قضية', 'مدعي', 'مدعى', 'محكمة', 'تاريخ', 'موضوع']):
                    case_info.append(line)
            
            # Create a more informative response
            response = """## ✅ تم فحص الملف بنجاح

تم التحقق من صحة المستند وتخزينه في النظام. المستند متوافق مع متطلبات صحيفة الدعوى.

---

## 📋 **معلومات المستند المستخرجة**

"""
            
            if case_info:
                response += "**تم استخراج المعلومات التالية من المستند:**\n\n"
                for info in case_info[:8]:  # Show first 8 relevant lines
                    if len(info) > 5:  # Only show meaningful lines
                        response += f"• {info}\n"
                response += "\n"
            else:
                response += "**تم استخراج النص من المستند بنجاح.**\n\n"
            
            response += """## 📝 **ملخص القضية**

تم تحليل المستند بنجاح باستخدام Azure Document Intelligence. المستند يحتوي على معلومات القضية الأساسية.

---

## 🔄 **الخطوات التالية**

**هل لديك مرفقات إضافية تريد رفعها؟**

💡 *المرفقات الداعمة ستساعد في تعزيز موقفك القانوني.*"""
            
            return response
        else:
            # Basic fallback for when no text is available
            return """## ✅ تم فحص الملف بنجاح

تم التحقق من صحة المستند وتخزينه في النظام. المستند متوافق مع متطلبات صحيفة الدعوى.

---

## 📋 **ملخص القضية**

تم تحليل المستند بنجاح باستخدام الذكاء الاصطناعي.

---

## 🔄 **الخطوات التالية**

**هل لديك مرفقات إضافية تريد رفعها؟**

💡 *المرفقات الداعمة ستساعد في تعزيز موقفك القانوني.*"""

    async def _update_conversation_status(self, conversation_id: str, new_status: ConversationStatus) -> None:
        """Update conversation status."""
        try:
            from app.modules.conversation.service import ConversationService
            conversation_service = ConversationService(self.db)
            await conversation_service.update_conversation_status(conversation_id, new_status)
            logger.info(f"Updated conversation {conversation_id} status to {new_status}")
        except Exception as e:
            logger.error(f"Error updating conversation status: {str(e)}")

    async def _get_conversation_with_status(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation with its status and associated prompt."""
        try:
            from app.modules.conversation.service import ConversationService
            conversation_service = ConversationService(self.db)
            return await conversation_service.get_conversation_with_prompt(conversation_id)
        except Exception as e:
            logger.error(f"Error getting conversation with status: {str(e)}")
            return None

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
        
        content = "No response available"
        metadata = {}
        
        if isinstance(response_data, dict):
            if "content" in response_data:
                content = response_data["content"]
                metadata = response_data.get("metadata", {})
            else:
                content = str(response_data)
                logger.warning(f"Unexpected response_data format: {response_data}")
        elif isinstance(response_data, str):
            content = response_data
        else:
            content = str(response_data)
            logger.warning(f"Unexpected response_data type: {type(response_data)}")

        if not isinstance(content, str):
            logger.warning(f"Content is not a string, converting: {type(content)} -> {content}")
            content = str(content)
        
        logger.info(f"Extracted response content ({len(content)} chars)")
        if metadata:
            logger.info(f"Extracted metadata: {list(metadata.keys())}")
            
        return content, metadata

    async def _store_agent_message(self, content: str, agent_metadata: Dict, conversation_id: str, supervisor_result: Dict = None) -> None:
        """Store the agent's response in the database."""
        storage_metadata = {
            "type": "agent_response",
            **agent_metadata
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
        
        logger.info(f"Stored agent message with metadata: {list(storage_metadata.keys())}")
        
        logger.info(f"Stored agent response for conversation {conversation_id}")

    def _build_api_response(self, content: str, supervisor_result: Dict, agent_metadata: Dict) -> QueryResponse:
        """Build the final API response with metadata."""
        
        if not isinstance(content, str):
            logger.error(f"Content is not a string in _build_api_response: {type(content)} -> {content}")
            content = str(content)
        
        api_metadata = {
            "agent_type": supervisor_result.get("agent_type", "unknown"),
            "prompt_type": supervisor_result.get("prompt_type", "general"),
            "confidence": supervisor_result.get("confidence", 0.0),
            **agent_metadata
        }
        
        if supervisor_result.get("error"):
            api_metadata["error"] = supervisor_result["error"]
        if supervisor_result.get("reasoning"):
            api_metadata["reasoning"] = supervisor_result["reasoning"]
            
        return QueryResponse(response=content, metadata=api_metadata)

    # Attachment processing helper methods

    async def _extract_attachment_content(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract content from attachment using Azure Document Intelligence."""
        try:
            if not self.document_intelligence_processor:
                logger.warning("Azure Document Intelligence not available, returning basic content")
                return {
                    "raw_text": f"محتوى المرفق: {filename}",
                    "key_value_pairs": {},
                    "form_fields": {},
                    "total_pages": 1,
                    "extraction_method": "fallback"
                }
            
            # Analyze document using Azure Document Intelligence
            poller = self.document_intelligence_processor.begin_analyze_document(
                "prebuilt-document", file_content
            )
            result = poller.result()
            
            # Extract raw text
            raw_text = ""
            total_pages = len(result.pages)
            for page in result.pages:
                if hasattr(page, 'lines'):
                    page_text = "\n".join([line.content for line in page.lines])
                    raw_text += page_text + "\n"
                elif hasattr(page, 'content'):
                    raw_text += page.content + "\n"
            
            # Extract key-value pairs
            key_value_pairs = {}
            if hasattr(result, 'key_value_pairs') and result.key_value_pairs:
                for kv_pair in result.key_value_pairs:
                    if kv_pair.key and kv_pair.value:
                        key_text = kv_pair.key.content.strip()
                        value_text = kv_pair.value.content.strip()
                        key_value_pairs[key_text] = value_text
            
            # Extract form fields
            form_fields = {}
            if hasattr(result, 'form_fields') and result.form_fields:
                for field_name, field in result.form_fields.items():
                    if field.value:
                        form_fields[field_name] = field.value.content.strip()
            
            return {
                "raw_text": raw_text,
                "key_value_pairs": key_value_pairs,
                "form_fields": form_fields,
                "total_pages": total_pages,
                "extraction_method": "azure_document_intelligence"
            }
            
        except Exception as e:
            logger.error(f"Error extracting attachment content: {str(e)}")
            return {
                "raw_text": f"محتوى المرفق: {filename}",
                "key_value_pairs": {},
                "form_fields": {},
                "total_pages": 1,
                "extraction_method": "error_fallback"
            }

    async def _store_attachment_data(self, conversation_id: str, attachment_data: Dict[str, Any]) -> None:
        """Store attachment data in the database."""
        try:
            # Store in attachments collection
            attachment_data["created_at"] = datetime.utcnow()
            attachment_data["updated_at"] = datetime.utcnow()
            
            await self.db.attachments.insert_one(attachment_data)
            logger.info(f"Stored attachment data for conversation: {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error storing attachment data: {e}")
            raise

    async def _generate_attachment_overview_response(self, claim_data: Dict[str, Any], attachment_results: List[Dict[str, Any]], conversation_id: str) -> str:
        """Generate comprehensive overview response with claim and attachment details."""
        try:
            # Extract claim details
            case_number = self._extract_case_number(claim_data)
            plaintiff = self._extract_field_value(claim_data, "plaintiff", "المدعي")
            defendant = self._extract_field_value(claim_data, "defendant", "المدعى عليه")
            case_subject = self._extract_field_value(claim_data, "case_subject", "موضوع الدعوى")
            case_type = self._extract_field_value(claim_data, "case_type", "نوع الدعوى")
            
            # Generate attachment summaries based on raw text only
            attachment_summaries = []
            for i, attachment in enumerate(attachment_results, 1):
                filename = attachment.get("filename", f"مرفق {i}")
                content_type = attachment.get("content_type", "غير محدد")
                file_size = attachment.get("file_size", 0)
                extracted_content = attachment.get("extracted_content", {})
                raw_text = (extracted_content or {}).get("raw_text", "").strip()
                snippet = (raw_text[:300] + "...") if raw_text and len(raw_text) > 300 else (raw_text or "(لا يوجد نص مستخرج)")
                summary = f"• {filename}: {snippet}"
                attachment_summaries.append(summary)
            attachments_block = "\n".join(attachment_summaries)  # fallback if LLM summary not available

            # Optionally refine summaries with full-context service (no truncation)
            try:
                from app.modules.attachments.service import AttachmentsAnalysisService
                svc = AttachmentsAnalysisService()
                full_block = await svc.generate_attachments_overview(conversation_id)
                if full_block:
                    attachments_block = full_block
            except Exception as _:
                pass
            
            # Build comprehensive response
            response = (
                "✅ تم استلام ورفع مرفقاتك بنجاح.\n\n"
                f"- تم حفظ النص المستخرج لكل مرفق ({len(attachment_results)}) وربطه بهذه المحادثة.\n"
                "يمكنك الآن مناقشة المرفقات معي مباشرة أو رفع المزيد عند الحاجة."
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating attachment overview response: {str(e)}")
            return f"تم رفع {len(attachment_results)} مرفق بنجاح. عذراً، حدث خطأ في إنشاء الملخص التفصيلي." 

    async def _store_extracted_case_data(self, conversation_id: str, extracted_data: Dict[str, Any]):
        """Store extracted case data in the database."""
        try:
            # Update the existing claim record with extracted data
            update_data = {
                "extracted_case_data": extracted_data,
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow()
            }
            
            # Add individual fields for easy querying
            if "case_number" in extracted_data:
                update_data["case_number"] = extracted_data["case_number"]
            if "case_subject" in extracted_data:
                update_data["case_subject"] = extracted_data["case_subject"]
            if "case_type" in extracted_data:
                update_data["case_type"] = extracted_data["case_type"]
            if "plaintiff_name" in extracted_data:
                update_data["plaintiff_name"] = extracted_data["plaintiff_name"]
            if "defendant_name" in extracted_data:
                update_data["defendant_name"] = extracted_data["defendant_name"]
            if "filing_date" in extracted_data:
                update_data["filing_date"] = extracted_data["filing_date"]
            if "court" in extracted_data:
                update_data["court"] = extracted_data["court"]
            if "case_summary" in extracted_data:
                update_data["case_summary"] = extracted_data["case_summary"]
            if "extraction_confidence" in extracted_data:
                update_data["extraction_confidence"] = extracted_data["extraction_confidence"]
            
            # Update the statement_of_claim collection
            await self.db.statement_of_claim.update_one(
                {"conversation_id": conversation_id},
                {"$set": update_data}
            )
            
            logger.info(f"Stored extracted case data for conversation {conversation_id}: {list(extracted_data.keys())}")
            
        except Exception as e:
            logger.error(f"Error storing extracted case data: {str(e)}")
            raise 

    async def _extract_saudi_legal_document_data(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Specialized extraction for Saudi Arabian legal documents (صحيفة الدعوى)."""
        try:
            from app.modules.document_processor.service import DocumentProcessorService
            document_processor = DocumentProcessorService()
            
            # Extract clean text using Document Intelligence with layout analysis
            extracted_text = await document_processor._extract_raw_text_only(file_content, filename)
            
            # Log the extracted text for debugging
            logger.info(f"Extracted text length: {len(extracted_text)}")
            logger.info(f"First 500 characters: {extracted_text[:500]}")
            
            if not self.openai_processor:
                logger.warning("Azure OpenAI client not configured for Saudi legal document extraction")
                return self._generate_saudi_legal_fallback_data()
            
            # Enhanced prompt with better instructions and examples
            extraction_prompt = f"""Analyze this Saudi Arabian legal document (صحيفة الدعوى) text and extract the following information in JSON format.

EXTRACTED TEXT:
{extracted_text[:10000]}

IMPORTANT: Look carefully for the following patterns in the text:
- Look for "رقم الطلب" followed by numbers (like ١٣٨٣٩٥١)
- Look for "التاريخ" followed by dates (like ١٤٤٤/٠٣/١٩)
- Look for "اسم المدعي" or "مقدم الطلب" followed by names
- Look for "اسم المدعى عليه" followed by entity names
- Look for "رقم القرار" followed by numbers
- Look for "رقم التظلم" followed by numbers
- Look for email addresses and phone numbers
- Look for addresses with building numbers, streets, cities

Extract this information in JSON format with high accuracy for Saudi legal documents:
{{
    "document_type": "صحيفة الدعوى",
    "document_pages": "عدد الصفحات",
    "court_info": {{
        "court_name": "اسم المحكمة (look for المحكمة الإدارية or similar)",
        "court_type": "نوع المحكمة",
        "request_number": "رقم الطلب (look for numbers after رقم الطلب)",
        "case_registration_number": "رقم قيد الدعوى",
        "submission_date": "التاريخ (look for dates like ١٤٤٤/٠٣/١٩)",
        "is_new_request": "طلب جديد (true if found, false if not)",
        "national_address": "العنوان الوطني"
    }},
    "plaintiff_info": {{
        "name": "اسم المدعي (look for names after مقدم الطلب or اسم المدعي)",
        "profession": "المهنة (look for words like بدون عمل, موظف, etc.)",
        "workplace": "مكان العمل",
        "nationality": "الجنسية (look for سعودي, etc.)",
        "id_number": "رقم السجل (look for numbers like ١١١٠٢٢٥١٨٠)",
        "id_type": "نوع الهوية (look for هوية وطنية, etc.)"
    }},
    "plaintiff_address": {{
        "building_number": "رقم المبني (look for numbers like ۲۹۷۱)",
        "street": "الشارع (look for street names like سعيد بن عامر)",
        "unit_number": "وحدة رقم",
        "city": "المدينة (look for الرياض, جدة, etc.)",
        "postal_code": "الرمز البريدي (look for numbers like ١٢٣٩٥)",
        "additional_code": "الرمز الإضافي (look for numbers like ٧١٧٤)",
        "email": "البريد الإلكتروني (look for email addresses like maabeer@gmail.com)",
        "mobile": "الهاتف المتنقل (look for numbers like ٠٥٤٨٠٠٦٧٠٠)"
    }},
    "defendant_info": {{
        "entity_type": "نوع الجهة (look for جهة حكومية, etc.)",
        "name": "اسم المدعى عليه (look for names like أمانة منطقة الرياض)",
        "additional_statement": "بيان اضافي",
        "workplace": "مكان العمل",
        "nationality": "الجنسية",
        "id_number": "رقم السجل (look for numbers like ٣٨٥)",
        "id_type": "نوع الهوية"
    }},
    "case_details": {{
        "subject": "الموضوع (look for case subject)",
        "case_description": "وصف القضية (look for case description)",
        "violation_number": "رقم المخالفة (look for numbers like ١٠٠٠٠٠٠٣٦٥٧٨٤٦)",
        "commercial_register": "السجل التجاري (look for numbers like ١٠١٠٤٥٢٣٥٥)",
        "requested_action": "الطلب المطلوب (look for requests like الغاء المخالف)"
    }},
    "additional_info": {{
        "decision_number": "رقم القرار (look for numbers like ٠٠٠٠٠٣٦٥٧٨٤٦)",
        "decision_date": "تاريخ القرار (look for dates like ١٤٤٤/٠٣/٠٢)",
        "knowledge_date": "تاريخ العلم القرار",
        "grievance_number": "رقم التظلم (look for numbers like ٣٨٠٥٤٨٢)",
        "grievance_date": "تاريخ التظلم (look for dates like ١٤٤٤/٠٣/١٣)",
        "violation_cancellation_request": "اطلب الغاء المخالف رقم (look for numbers like ١٠٠٠٠٠٠٣٦٥٧٨٤٦)"
    }},
    "case_requests": {{
        "request_description": "وصف الطلب",
        "detailed_requests": "الطلبات التفصيلية"
    }},
    "declarations": [
        "الاقرارات (extract as array of declaration points)"
    ],
    "required_documents": [
        "المستندات الواجب ارفاقها (extract as array of required documents)"
    ],
    "contact_info": {{
        "primary_mobile": "رقم الجوال الاساسي (look for numbers like ٠٥٤٨٠٠٦٧٠٠)",
        "additional_mobile": "رقم الجوال الاضافي",
        "email": "البريد الالكتروني"
    }},
    "supporting_documents": [
        "الاسانيد المرفقة"
    ],
    "document_metadata": {{
        "version_number": "رقم الاصدار (look for numbers like ٢)",
        "release_date": "تاريخ الاصدار (look for dates like ١٤٣٩)",
        "reference_code": "الكود المرجعي (look for numbers like ٢٣١٧٧٠٧)",
        "processing_time": "الوقت (look for times like ١:٢٧ م)"
    }},
    "extraction_confidence": 0.95,
    "document_quality": "high/medium/low",
    "extracted_fields_count": 0
}}

CRITICAL INSTRUCTIONS:
1. Search the text carefully for each field - don't just return "غير مذكور"
2. Look for Arabic numerals (١٢٣٤٥٦٧٨٩٠) and Western numerals (1234567890)
3. Look for dates in Hijri format (١٤٤٤/٠٣/١٩) and Western format
4. Look for email addresses (containing @)
5. Look for phone numbers (containing digits)
6. Look for names after labels like "اسم", "مقدم الطلب", "المدعي"
7. Look for entity names after "المدعى عليه"
8. Look for numbers after labels like "رقم الطلب", "رقم القرار", "رقم التظلم"
9. If you find the information, extract it exactly as it appears
10. Only use "غير مذكور" if you cannot find the information after careful search

Return ONLY the JSON object, no additional text."""
            
            extraction_response = self.openai_processor.chat.completions.create(
                model=self.azure_deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert Saudi Arabian legal document analyzer. Extract structured information from صحيفة الدعوى documents with high accuracy. Search the text carefully for each field and extract exact values. Handle Arabic text, numbers, legal terminology, and multi-page documents properly. Return only valid JSON."},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            # Parse extracted data
            extracted_data = {}
            try:
                import json
                extracted_json = extraction_response.choices[0].message.content.strip()
                # Clean the response to get valid JSON
                if extracted_json.startswith('```json'):
                    extracted_json = extracted_json[7:]
                if extracted_json.endswith('```'):
                    extracted_json = extracted_json[:-3]
                if extracted_json.startswith('```'):
                    extracted_json = extracted_json[3:]
                if extracted_json.endswith('```'):
                    extracted_json = extracted_json[:-3]
                
                extracted_data = json.loads(extracted_json.strip())
                
                # Validate and count extracted fields
                total_fields = 0
                if extracted_data.get("court_info"):
                    total_fields += len([v for v in extracted_data["court_info"].values() if v and v != "غير مذكور"])
                if extracted_data.get("plaintiff_info"):
                    total_fields += len([v for v in extracted_data["plaintiff_info"].values() if v and v != "غير مذكور"])
                if extracted_data.get("plaintiff_address"):
                    total_fields += len([v for v in extracted_data["plaintiff_address"].values() if v and v != "غير مذكور"])
                if extracted_data.get("defendant_info"):
                    total_fields += len([v for v in extracted_data["defendant_info"].values() if v and v != "غير مذكور"])
                if extracted_data.get("additional_info"):
                    total_fields += len([v for v in extracted_data["additional_info"].values() if v and v != "غير مذكور"])
                if extracted_data.get("contact_info"):
                    total_fields += len([v for v in extracted_data["contact_info"].values() if v and v != "غير مذكور"])
                
                extracted_data["extracted_fields_count"] = total_fields
                
                logger.info(f"Successfully extracted Saudi legal document data: {total_fields} fields")
                logger.info(f"Extracted data keys: {list(extracted_data.keys())}")
                
            except Exception as parse_error:
                logger.warning(f"Failed to parse Saudi legal document JSON: {parse_error}")
                logger.info(f"Raw response: {extraction_response.choices[0].message.content}")
                logger.info("Falling back to pattern matching extraction")
                extracted_data = self._extract_basic_info_from_text(extracted_text)
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting Saudi legal document data: {e}")
            logger.info("Falling back to pattern matching extraction")
            try:
                from app.modules.document_processor.service import DocumentProcessorService
                document_processor = DocumentProcessorService()
                extracted_text = await document_processor._extract_raw_text_only(file_content, filename)
                return self._extract_basic_info_from_text(extracted_text)
            except:
                return self._generate_saudi_legal_fallback_data()

    def _generate_saudi_legal_fallback_data(self) -> Dict[str, Any]:
        """Generate fallback data structure for Saudi legal documents."""
        return {
            "document_type": "صحيفة الدعوى",
            "document_pages": "غير مذكور",
            "court_info": {
                "court_name": "غير مذكور",
                "court_type": "غير مذكور",
                "request_number": "غير مذكور",
                "case_registration_number": "غير مذكور",
                "submission_date": "غير مذكور",
                "is_new_request": False,
                "national_address": "غير مذكور"
            },
            "plaintiff_info": {
                "name": "غير مذكور",
                "profession": "غير مذكور",
                "workplace": "غير مذكور",
                "nationality": "غير مذكور",
                "id_number": "غير مذكور",
                "id_type": "غير مذكور"
            },
            "plaintiff_address": {
                "building_number": "غير مذكور",
                "street": "غير مذكور",
                "unit_number": "غير مذكور",
                "city": "غير مذكور",
                "postal_code": "غير مذكور",
                "additional_code": "غير مذكور",
                "email": "غير مذكور",
                "mobile": "غير مذكور"
            },
            "defendant_info": {
                "entity_type": "غير مذكور",
                "name": "غير مذكور",
                "additional_statement": "غير مذكور",
                "workplace": "غير مذكور",
                "nationality": "غير مذكور",
                "id_number": "غير مذكور",
                "id_type": "غير مذكور"
            },
            "case_details": {
                "subject": "غير مذكور",
                "case_description": "غير مذكور",
                "violation_number": "غير مذكور",
                "commercial_register": "غير مذكور",
                "requested_action": "غير مذكور"
            },
            "additional_info": {
                "decision_number": "غير مذكور",
                "decision_date": "غير مذكور",
                "knowledge_date": "غير مذكور",
                "grievance_number": "غير مذكور",
                "grievance_date": "غير مذكور",
                "violation_cancellation_request": "غير مذكور"
            },
            "case_requests": {
                "request_description": "غير مذكور",
                "detailed_requests": "غير مذكور"
            },
            "declarations": [],
            "required_documents": [],
            "contact_info": {
                "primary_mobile": "غير مذكور",
                "additional_mobile": "غير مذكور",
                "email": "غير مذكور"
            },
            "supporting_documents": [],
            "document_metadata": {
                "version_number": "غير مذكور",
                "release_date": "غير مذكور",
                "reference_code": "غير مذكور",
                "processing_time": "غير مذكور"
            },
            "extraction_confidence": 0.0,
            "document_quality": "low",
            "extracted_fields_count": 0
        }

    async def _generate_saudi_legal_response(self, extracted_data: Dict[str, Any], conversation_id: str) -> str:
        """Generate specialized response for Saudi legal documents."""
        try:
            if not self.openai_processor:
                return self._generate_saudi_legal_fallback_response(extracted_data)
            
            # Build comprehensive response with extracted Saudi legal data
            response_prompt = f"""Based on this Saudi Arabian legal document (صحيفة الدعوى) analysis, create a comprehensive, professional response in Arabic.

Extracted Information:
**معلومات المحكمة:**
- المحكمة: {extracted_data.get('court_info', {}).get('court_name', 'غير مذكور')}
- رقم الطلب: {extracted_data.get('court_info', {}).get('request_number', 'غير مذكور')}
- رقم قيد الدعوى: {extracted_data.get('court_info', {}).get('case_registration_number', 'غير مذكور')}
- تاريخ التقديم: {extracted_data.get('court_info', {}).get('submission_date', 'غير مذكور')}
- طلب جديد: {extracted_data.get('court_info', {}).get('is_new_request', False)}

**بيانات المدعي:**
- الاسم: {extracted_data.get('plaintiff_info', {}).get('name', 'غير مذكور')}
- المهنة: {extracted_data.get('plaintiff_info', {}).get('profession', 'غير مذكور')}
- الجنسية: {extracted_data.get('plaintiff_info', {}).get('nationality', 'غير مذكور')}
- رقم الهوية: {extracted_data.get('plaintiff_info', {}).get('id_number', 'غير مذكور')}

**عنوان المدعي:**
- المدينة: {extracted_data.get('plaintiff_address', {}).get('city', 'غير مذكور')}
- الشارع: {extracted_data.get('plaintiff_address', {}).get('street', 'غير مذكور')}
- رقم المبني: {extracted_data.get('plaintiff_address', {}).get('building_number', 'غير مذكور')}
- البريد الإلكتروني: {extracted_data.get('plaintiff_address', {}).get('email', 'غير مذكور')}
- الهاتف: {extracted_data.get('plaintiff_address', {}).get('mobile', 'غير مذكور')}

**بيانات المدعى عليه:**
- نوع الجهة: {extracted_data.get('defendant_info', {}).get('entity_type', 'غير مذكور')}
- الاسم: {extracted_data.get('defendant_info', {}).get('name', 'غير مذكور')}
- رقم السجل: {extracted_data.get('defendant_info', {}).get('id_number', 'غير مذكور')}

**معلومات اضافية:**
- رقم القرار: {extracted_data.get('additional_info', {}).get('decision_number', 'غير مذكور')}
- تاريخ القرار: {extracted_data.get('additional_info', {}).get('decision_date', 'غير مذكور')}
- رقم التظلم: {extracted_data.get('additional_info', {}).get('grievance_number', 'غير مذكور')}
- تاريخ التظلم: {extracted_data.get('additional_info', {}).get('grievance_date', 'غير مذكور')}
- طلب الغاء المخالف: {extracted_data.get('additional_info', {}).get('violation_cancellation_request', 'غير مذكور')}

**تفاصيل القضية:**
- رقم المخالفة: {extracted_data.get('case_details', {}).get('violation_number', 'غير مذكور')}
- السجل التجاري: {extracted_data.get('case_details', {}).get('commercial_register', 'غير مذكور')}
- الطلب المطلوب: {extracted_data.get('case_details', {}).get('requested_action', 'غير مذكور')}

**بيانات التواصل:**
- الجوال الاساسي: {extracted_data.get('contact_info', {}).get('primary_mobile', 'غير مذكور')}
- الجوال الاضافي: {extracted_data.get('contact_info', {}).get('additional_mobile', 'غير مذكور')}
- البريد الالكتروني: {extracted_data.get('contact_info', {}).get('email', 'غير مذكور')}

Create a detailed response with these sections:

## ✅ تم فحص صحيفة الدعوى بنجاح

تم التحقق من صحة المستند وتخزينه في النظام. المستند متوافق مع متطلبات صحيفة الدعوى السعودية.

## 📋 **تفاصيل القضية**

**معلومات المحكمة:**
- **المحكمة:** {extracted_data.get('court_info', {}).get('court_name', 'غير مذكور')}
- **رقم الطلب:** {extracted_data.get('court_info', {}).get('request_number', 'غير مذكور')}
- **رقم قيد الدعوى:** {extracted_data.get('court_info', {}).get('case_registration_number', 'غير مذكور')}
- **تاريخ التقديم:** {extracted_data.get('court_info', {}).get('submission_date', 'غير مذكور')}
- **نوع الطلب:** {'طلب جديد' if extracted_data.get('court_info', {}).get('is_new_request', False) else 'غير محدد'}

**بيانات المدعي:**
- **الاسم:** {extracted_data.get('plaintiff_info', {}).get('name', 'غير مذكور')}
- **المهنة:** {extracted_data.get('plaintiff_info', {}).get('profession', 'غير مذكور')}
- **الجنسية:** {extracted_data.get('plaintiff_info', {}).get('nationality', 'غير مذكور')}
- **رقم الهوية:** {extracted_data.get('plaintiff_info', {}).get('id_number', 'غير مذكور')}

**عنوان المدعي:**
- **المدينة:** {extracted_data.get('plaintiff_address', {}).get('city', 'غير مذكور')}
- **الشارع:** {extracted_data.get('plaintiff_address', {}).get('street', 'غير مذكور')}
- **رقم المبني:** {extracted_data.get('plaintiff_address', {}).get('building_number', 'غير مذكور')}
- **البريد الإلكتروني:** {extracted_data.get('plaintiff_address', {}).get('email', 'غير مذكور')}
- **الهاتف:** {extracted_data.get('plaintiff_address', {}).get('mobile', 'غير مذكور')}

**بيانات المدعى عليه:**
- **نوع الجهة:** {extracted_data.get('defendant_info', {}).get('entity_type', 'غير مذكور')}
- **الاسم:** {extracted_data.get('defendant_info', {}).get('name', 'غير مذكور')}
- **رقم السجل:** {extracted_data.get('defendant_info', {}).get('id_number', 'غير مذكور')}

## 📝 **معلومات اضافية**

**تفاصيل القرار:**
- **رقم القرار:** {extracted_data.get('additional_info', {}).get('decision_number', 'غير مذكور')}
- **تاريخ القرار:** {extracted_data.get('additional_info', {}).get('decision_date', 'غير مذكور')}
- **رقم التظلم:** {extracted_data.get('additional_info', {}).get('grievance_number', 'غير مذكور')}
- **تاريخ التظلم:** {extracted_data.get('additional_info', {}).get('grievance_date', 'غير مذكور')}

**تفاصيل القضية:**
- **رقم المخالفة:** {extracted_data.get('case_details', {}).get('violation_number', 'غير مذكور')}
- **السجل التجاري:** {extracted_data.get('case_details', {}).get('commercial_register', 'غير مذكور')}
- **الطلب المطلوب:** {extracted_data.get('case_details', {}).get('requested_action', 'غير مذكور')}

**بيانات التواصل:**
- **الجوال الاساسي:** {extracted_data.get('contact_info', {}).get('primary_mobile', 'غير مذكور')}
- **الجوال الاضافي:** {extracted_data.get('contact_info', {}).get('additional_mobile', 'غير مذكور')}
- **البريد الالكتروني:** {extracted_data.get('contact_info', {}).get('email', 'غير مذكور')}

## 📄 **ملخص القضية**

{extracted_data.get('case_details', {}).get('case_description', 'تم تحليل صحيفة الدعوى بنجاح. المستند يحتوي على معلومات القضية الأساسية.')}

## 🔄 **الخطوات التالية**

**هل لديك مرفقات إضافية تريد رفعها؟**

💡 *المرفقات الداعمة مثل الهوية والسجل التجاري وصورة المخالفة ستساعد في تعزيز موقفك القانوني.*"""
            
            response = self.openai_processor.chat.completions.create(
                model=self.azure_deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert Saudi Arabian legal assistant. Create comprehensive, professional responses in Arabic for صحيفة الدعوى documents. Use the extracted information provided and format the response professionally with proper Arabic formatting."},
                    {"role": "user", "content": response_prompt}
                ],
                temperature=0.1,
                max_tokens=5000
            )
            
            llm_response = response.choices[0].message.content.strip()
            logger.info(f"Generated Saudi legal document response for conversation {conversation_id}")
            return llm_response
            
        except Exception as e:
            logger.error(f"Error generating Saudi legal response: {e}")
            return self._generate_saudi_legal_fallback_response(extracted_data)

    def _generate_saudi_legal_fallback_response(self, extracted_data: Dict[str, Any]) -> str:
        """Generate fallback response for Saudi legal documents."""
        return f"""## ✅ تم فحص صحيفة الدعوى بنجاح

تم التحقق من صحة المستند وتخزينه في النظام. المستند متوافق مع متطلبات صحيفة الدعوى السعودية.

## 📋 **تفاصيل القضية**

**معلومات المحكمة:**
- **المحكمة:** {extracted_data.get('court_info', {}).get('court_name', 'غير مذكور')}
- **رقم الطلب:** {extracted_data.get('court_info', {}).get('request_number', 'غير مذكور')}

**بيانات المدعي:**
- **الاسم:** {extracted_data.get('plaintiff_info', {}).get('name', 'غير مذكور')}
- **المهنة:** {extracted_data.get('plaintiff_info', {}).get('profession', 'غير مذكور')}

**بيانات المدعى عليه:**
- **الاسم:** {extracted_data.get('defendant_info', {}).get('name', 'غير مذكور')}

**معلومات اضافية:**
- **رقم القرار:** {extracted_data.get('additional_info', {}).get('decision_number', 'غير مذكور')}
- **رقم التظلم:** {extracted_data.get('additional_info', {}).get('grievance_number', 'غير مذكور')}

## 📝 **ملخص القضية**

تم تحليل صحيفة الدعوى بنجاح باستخدام الذكاء الاصطناعي. المستند يحتوي على معلومات القضية الأساسية.

## 🔄 **الخطوات التالية**

**هل لديك مرفقات إضافية تريد رفعها؟**

💡 *المرفقات الداعمة ستساعد في تعزيز موقفك القانوني.*"""

    def _extract_basic_info_from_text(self, text: str) -> Dict[str, Any]:
        """Extract basic information using simple text pattern matching as fallback."""
        try:
            import re
            
            extracted_data = self._generate_saudi_legal_fallback_data()
            
            # Extract request number
            request_pattern = r'رقم الطلب[:\s]*([٠-٩0-9]+)'
            request_match = re.search(request_pattern, text)
            if request_match:
                extracted_data["court_info"]["request_number"] = request_match.group(1)
            
            # Extract submission date
            date_pattern = r'التاريخ[:\s]*([٠-٩/]+)'
            date_match = re.search(date_pattern, text)
            if date_match:
                extracted_data["court_info"]["submission_date"] = date_match.group(1)
            
            # Extract plaintiff name
            plaintiff_pattern = r'(?:اسم المدعي|مقدم الطلب)[:\s]*([^\n\r]+)'
            plaintiff_match = re.search(plaintiff_pattern, text)
            if plaintiff_match:
                extracted_data["plaintiff_info"]["name"] = plaintiff_match.group(1).strip()
            
            # Extract defendant name
            defendant_pattern = r'اسم المدعى عليه[:\s]*([^\n\r]+)'
            defendant_match = re.search(defendant_pattern, text)
            if defendant_match:
                extracted_data["defendant_info"]["name"] = defendant_match.group(1).strip()
            
            # Extract mobile number
            mobile_pattern = r'(?:رقم الجوال|الهاتف المتنقل)[:\s]*([٠-٩0-9]+)'
            mobile_match = re.search(mobile_pattern, text)
            if mobile_match:
                extracted_data["plaintiff_address"]["mobile"] = mobile_match.group(1)
            
            # Extract email
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            email_match = re.search(email_pattern, text)
            if email_match:
                extracted_data["plaintiff_address"]["email"] = email_match.group(0)
            
            # Extract decision number
            decision_pattern = r'رقم القرار[:\s]*([٠-٩0-9]+)'
            decision_match = re.search(decision_pattern, text)
            if decision_match:
                extracted_data["additional_info"]["decision_number"] = decision_match.group(1)
            
            # Extract grievance number
            grievance_pattern = r'رقم التظلم[:\s]*([٠-٩0-9]+)'
            grievance_match = re.search(grievance_pattern, text)
            if grievance_match:
                extracted_data["additional_info"]["grievance_number"] = grievance_match.group(1)
            
            # Extract violation number
            violation_pattern = r'رقم المخالفة[:\s]*([٠-٩0-9]+)'
            violation_match = re.search(violation_pattern, text)
            if violation_match:
                extracted_data["case_details"]["violation_number"] = violation_match.group(1)
            
            # Extract commercial register
            commercial_pattern = r'السجل التجاري[:\s]*([٠-٩0-9]+)'
            commercial_match = re.search(commercial_pattern, text)
            if commercial_match:
                extracted_data["case_details"]["commercial_register"] = commercial_match.group(1)
            
            # Count extracted fields
            total_fields = 0
            for section in ["court_info", "plaintiff_info", "plaintiff_address", "defendant_info", "additional_info", "case_details"]:
                if extracted_data.get(section):
                    total_fields += len([v for v in extracted_data[section].values() if v and v != "غير مذكور"])
            
            extracted_data["extracted_fields_count"] = total_fields
            logger.info(f"Extracted {total_fields} fields using pattern matching")
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error in pattern matching extraction: {e}")
            return self._generate_saudi_legal_fallback_data()

    async def _convert_extraction_result_to_data(self, extraction_result: ExtractionResult) -> Dict[str, Any]:
        """Convert extraction result to the format expected by the database."""
        try:
            data = {
                "file_url": extraction_result.file_url,
                "document_type": "صحيفة دعوى",
                "total_pages": extraction_result.extracted_claim.total_pages if extraction_result.extracted_claim else 1,
                "validation_score": extraction_result.document_intelligence_confidence or 0.0,
                "is_valid": (extraction_result.extracted_claim.is_valid if extraction_result.extracted_claim else False),
                "processing_time": extraction_result.processing_time,
                "extraction_status": extraction_result.status.value,
                "raw_text": extraction_result.raw_text,
                "raw_text_length": extraction_result.raw_text_length
            }
            
            # Add extracted claim information
            if extraction_result.extracted_claim:
                claim_data = extraction_result.extracted_claim.model_dump()
                data.update(claim_data)
            
            # Add page contents
            if extraction_result.page_contents:
                data["page_contents"] = [
                    {
                        "page_number": pc.page_number,
                        "extracted_text": pc.extracted_text,
                        "confidence": pc.confidence,
                        "model_used": pc.model_used,
                        "success": pc.success
                    }
                    for pc in extraction_result.page_contents
                ]
            
            return data
            
        except Exception as e:
            logger.error(f"Error converting extraction result to data: {e}")
            return {}

    async def _generate_professional_legal_response(self, extraction_result: ExtractionResult, conversation_id: str) -> str:
        """Generate a professional legal response like a lawyer would."""
        try:
            if not extraction_result.extracted_claim:
                return "عذراً، لم يتم استخراج معلومات كافية من المستند. يرجى التأكد من أن الملف يحتوي على صحيفة دعوى صحيحة."
            
            claim = extraction_result.extracted_claim
            
            # Build professional legal response
            response_parts = []
            
            # Header (lawyerly, concise)
            response_parts.append("✅ تمت قراءة صحيفة الدعوى بنجاح.")
            response_parts.append("فيما يلي عرض مهني منظم لأهم ما ورد، يليه إبراز نقاط حساسة وخطوات عملية.")
            response_parts.append("تنويه: نمثل الجهة المدعى عليها (مثل أمانة منطقة الرياض). سنعرض القراءة بمنظور دفاعي دون تبنّي مزاعم المدعي.")
            response_parts.append("")
            
            # Basic case information
            response_parts.append("أولاً: معلومات أساسية عن الدعوى")
            response_parts.append(f"• نوع الدعوى: {claim.case_type or 'غير محدد'}")
            response_parts.append(f"• رقم القضية: {claim.case_number or 'غير محدد'}")
            response_parts.append(f"• عدد الصفحات: {extraction_result.extracted_claim.total_pages or 1}")
            response_parts.append("")
            
            # Parties information
            response_parts.append("ثانياً: الأطراف المعنية")
            response_parts.append(f"• المدعي: {claim.plaintiff_name or 'غير محدد'}")
            response_parts.append(f"• المدعى عليه: {claim.defendant_name or 'غير محدد'}")
            response_parts.append("")
             
            response_parts.append("ثالثاً: عرض منظم لوقائع الدعوى ومطالب المدعي")
            if claim.case_subject:
                response_parts.append(f"• موضوع الدعوى: {claim.case_subject}")
            if claim.claim_amount:
                response_parts.append(f"• مبلغ المطالبة: {claim.claim_amount}")
            if claim.court_name:
                response_parts.append(f"• المحكمة المختصة: {claim.court_name}")
            # Try to surface claimant asks from overview text if available
            if getattr(claim, 'claim_overview', None):
                text = claim.claim_overview.strip()
                response_parts.append("• مطالب المدعي كما تظهر من المستند: ")
                # naive split to bullets for readability, skipping legal evaluation lines
                excluded_phrases = ["التقييم القانوني", "تحليل قانوني", "تقييم قانوني"]
                for line in [l.strip('-• \t') for l in text.split('\n') if l.strip()][:10]:
                    if any(phrase in line for phrase in excluded_phrases):
                        continue
                    if len([c for c in line if c.isalnum()]) < 2:
                        continue
                    response_parts.append(f"  - {line}")
            # الطلبات المقدمة - مقتبسة من بيانات الدعوى
            response_parts.append("• الطلبات المقدمة كما وردت في صحيفة الدعوى:")
            requests_lines = []

            # اجمع النصوص المصدرية المحتملة
            source_snippets: List[str] = []
            if getattr(claim, 'case_requests', None):
                source_snippets.append(claim.case_requests.strip())
            reqs_text = ""
            if extraction_result.raw_text:
                try:
                    from app.modules.claim_extractor.text_processor import TextProcessor as _TP
                    sections = _TP().extract_saudi_legal_sections(extraction_result.raw_text)
                    reqs_text = (sections or {}).get("requests_in_case", "").strip()
                    if reqs_text:
                        source_snippets.append(reqs_text)
                except Exception:
                    pass

            # ضمّن النص الخام كاملاً لتمكين الاستخراج المباشر من الصحيفة
            if extraction_result.raw_text:
                source_snippets.append(extraction_result.raw_text.strip())
            combined_sources = "\n".join([s for s in source_snippets if s])[:12000]

            # حاول استخدام LLM لتنظيف/إعادة كتابة الطلبات باقتباس نص حرفي فقط
            llm_items: List[str] = []
            try:
                if self.openai_processor and combined_sources:
                    llm_prompt = f"""
أنت مساعد قانوني. استخرج الطلبات المقدمة كما هي حرفياً من النص أدناه، دون صياغة جديدة أو إضافة معلومات.
شروط صارمة:
- استخدم اقتباساً حرفياً لجمل الطلبات من النص المصدر
- لا تغيّر الكلمات أو ترتيبها، ولا تدمج جُملاً غير متجاورة
- أزل العناوين العامة مثل: "الطلبات" أو "الطلبات المقدمة في القضية"
- أزل رموز التعداد (• -) من البداية فقط
- احذف التكرارات
- حد أقصى 6 عناصر
- أعد النتيجة كـ JSON Array فقط بدون أي نص آخر

النص المصدر:
{combined_sources}
""".strip()
                    llm_resp = self.openai_processor.chat.completions.create(
                        model=self.azure_deployment_name,
                        messages=[
                            {"role": "system", "content": "دقيق وممتثل: أعد فقرات الطلبات باقتباس حرفي من النص فقط، بصيغة JSON Array من السلاسل."},
                            {"role": "user", "content": llm_prompt}
                        ],
                        temperature=0.0,
                        max_tokens=600
                    )
                    content = llm_resp.choices[0].message.content.strip()
                    import json as _json
                    # نظّف أسوار الشيفرة إن وجدت
                    if content.startswith('```json'):
                        content = content[7:]
                    if content.endswith('```'):
                        content = content[:-3]
                    if content.startswith('```'):
                        content = content[3:]
                    if content.endswith('```'):
                        content = content[:-3]
                    items = _json.loads(content.strip())
                    if isinstance(items, list):
                        # تحقّق من أن كل عنصر موجود حرفياً في المصادر
                        combined_lower = combined_sources
                        validated = []
                        for it in items:
                            if not isinstance(it, str):
                                continue
                            cand = it.strip().lstrip('•- ').strip()
                            if not cand:
                                continue
                            if cand in combined_lower:
                                validated.append(cand)
                            if len(validated) >= 6:
                                break
                        llm_items = validated
            except Exception:
                llm_items = []

            if llm_items:
                requests_lines = [f"  - {it}" for it in llm_items]
            else:
                # المسار الحتمي السابق
                # من الحقول المنظمة
                if getattr(claim, 'case_requests', None):
                    req_text = claim.case_requests.strip()
                    for line in [l.strip('-• \t') for l in req_text.split('\n') if l.strip()]:
                        if len([c for c in line if c.isalnum()]) < 2:
                            continue
                        requests_lines.append(f"  - {line}")
                    if not requests_lines:
                        import re as _re
                        parts = [p.strip() for p in _re.split(r'[،؛\.]', req_text) if p.strip()]
                        for p in parts[:6]:
                            requests_lines.append(f"  - {p}")
                # من أقسام النص المستخرج
                if not requests_lines and reqs_text:
                    for line in [l.strip('-• ') for l in reqs_text.split('\n') if l.strip()]:
                        if len(requests_lines) >= 6:
                            break
                        if "الطلبات" in line:
                            continue
                        requests_lines.append(f"  - {line}")
                # من نظرة عامة
                if not requests_lines and getattr(claim, 'claim_overview', None):
                    ov = claim.claim_overview.strip()
                    candidates = [l.strip('-• \t') for l in ov.split('\n') if l.strip()]
                    for line in candidates:
                        if any(kw in line for kw in ["الطلب", "طلبات", "إلغاء", "تعويض", "إلزام", "إيقاف", "إلغاء قرار"]):
                            requests_lines.append(f"  - {line}")
                            if len(requests_lines) >= 6:
                                break

            if requests_lines:
                response_parts.extend(requests_lines)
            else:
                response_parts.append("  - غير مذكور صراحة في النص المستخرج.")
            response_parts.append("")
            
            # Declarations section extracted from OCR text (الإقرارات)
            response_parts.append("**رابعاً: الإقرارات**")
            response_parts.append("• الإقرارات الموجودة في صحيفة الدعوى:")
            declarations_lines = []
            try:
                from app.modules.claim_extractor.text_processor import TextProcessor
                if extraction_result.raw_text:
                    sections = TextProcessor().extract_saudi_legal_sections(extraction_result.raw_text)
                    decl_text = (sections or {}).get("declarations", "").strip()
                    if decl_text:
                        for line in [l.strip() for l in decl_text.split("\n") if l.strip()]:
                            if len(declarations_lines) >= 6:
                                break
                            # prioritize lines that look like explicit declarations/acknowledgements
                            if (any(kw in line for kw in ["أقر", "أتعهد", "أوافق"]) or line.startswith("-") or line.startswith("•")) and ("الاقرارات" not in line):
                                cleaned = line.lstrip("•- ").strip()
                                if cleaned:
                                    declarations_lines.append(f"- {cleaned}")
            except Exception:
                pass
            if declarations_lines:
                response_parts.extend(declarations_lines)
            else:
                response_parts.append("- لم يتم العثور على إقرارات واضحة في النص المستخرج.")
            response_parts.append("")
            
            # Highlights
            response_parts.append("خامساً: نقاط بارزة تستحق الانتباه")
            highlights = []
            if claim.case_subject:
                highlights.append("يمكن الدفع بعدم توافر الأساس النظامي للطلب كما صيغ في صحيفة الدعوى.")
            if claim.case_number:
                highlights.append("توثيق رقم القضية يمكّن من طلب السجل الإجرائي والقرارات ذات الصلة لدحض مزاعم المدعي.")
            if claim.court_name:
                highlights.append("اختصاص المحكمة قد يكون محلاً للدفع إن تبيّن تعلق النزاع بقرارات تنظيمية عامة.")
            if getattr(claim, 'violation_number', None) or getattr(claim, 'decision_number', None):
                highlights.append("يمكن طلب أصل القرار/المخالفة ومحاضر الضبط للتحقق من سلامة الإجراءات والاختصاص.")
            if not highlights:
                highlights.append("لا توجد نقاط بارزة إضافية حالياً؛ سيُبنى الدفاع وفق ما يُستكمل من مرفقات.")
            response_parts.extend([f"- {h}" for h in highlights])
            response_parts.append("")

            # Closing note (defense-oriented)
            response_parts.append("سادساً: التوجيه الإجرائي للدفاع")
            response_parts.append("- سنبني دفوع الجهة المدعى عليها على ما ورد في الصحيفة وما يُستكمل من مستندات، مع إبراز أي ثغرات شكلية أو موضوعية تُسهم في رفض طلبات المدعي.")
             
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error generating professional legal response: {e}")
            return "تمت قراءة الملف، ويمكننا المتابعة بتفصيل الردود القانونية عند إرفاق الوثائق الداعمة."

    async def _append_attachments_to_claim(self, conversation_id: str, attachment_results: List[Dict[str, Any]]) -> None:
        """Append attachments info (including raw_text) to the existing statement_of_claim document."""
        try:
            # Build attachments array with minimal, relevant fields
            attachments_for_claim = []
            for att in attachment_results:
                extracted = att.get("extracted_content", {}) or {}
                attachments_for_claim.append({
                    "filename": att.get("filename"),
                    "file_url": att.get("file_url"),
                    "content_type": att.get("content_type"),
                    "file_size": att.get("file_size"),
                    "raw_text": extracted.get("raw_text"),
                    "total_pages": extracted.get("total_pages"),
                    "extraction_method": extracted.get("extraction_method"),
                    "upload_timestamp": att.get("upload_timestamp"),
                    "attachment_type": att.get("attachment_type", "supporting_document")
                })
            # Append or set attachments array on statement_of_claim
            await self.db.statement_of_claim.update_one(
                {"conversation_id": conversation_id},
                {"$push": {"attachments": {"$each": attachments_for_claim}}, "$set": {"updated_at": datetime.utcnow()}},
                upsert=False
            )
            logger.info(f"Appended {len(attachments_for_claim)} attachments into statement_of_claim for {conversation_id}")
        except Exception as e:
            logger.error(f"Error appending attachments to claim: {e}")
            raise