"""
Document Processor Service

This service handles document processing, validation, and data extraction.
It provides a clean interface for processing uploaded documents and validating
them against configured schemas.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json
from pathlib import Path

from app.core.config.document_schemas import (
    get_document_schema, 
    validate_document_data,
    DocumentSchema
)
from app.core.config.settings import get_settings
from azure.storage.blob import BlobServiceClient
import uuid

logger = logging.getLogger(__name__)


class DocumentProcessorService:
    """Service for processing and validating documents."""
    
    def __init__(self):
        self.settings = get_settings()
        self._blob_service_client = None
    
    @property
    def blob_service_client(self) -> BlobServiceClient:
        """Get or create blob service client."""
        if self._blob_service_client is None:
            self._blob_service_client = BlobServiceClient.from_connection_string(
                self.settings.AZURE_STORAGE_CONNECTION_STRING
            )
        return self._blob_service_client
    
    async def process_document(
        self, 
        file_content: bytes, 
        filename: str, 
        conversation_id: str,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a document file and extract/validate data.
        
        Args:
            file_content: Raw file content
            filename: Original filename
            conversation_id: Associated conversation ID
            document_type: Expected document type (auto-detected if None)
            
        Returns:
            Processed document data with validation results
        """
        try:
            # Upload file to blob storage
            file_url = await self._upload_file_to_blob(file_content, filename, conversation_id)
            
            # Extract document data
            extracted_data = await self._extract_document_data(file_content, filename, document_type)
            
            # Validate extracted data
            is_valid, validation_score, validation_errors = self._validate_document(extracted_data)
            
            # Update extracted data with validation results
            extracted_data.update({
                "validation_score": validation_score,
                "is_valid": is_valid,
                "validation_errors": validation_errors,
                "file_url": file_url,
                "conversation_id": conversation_id,
                "processing_timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Document processed successfully: {filename}, Valid: {is_valid}, Score: {validation_score}")
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error processing document {filename}: {e}")
            raise
    
    async def _upload_file_to_blob(self, file_content: bytes, filename: str, conversation_id: str) -> str:
        """Upload file to Azure Blob Storage."""
        try:
            if not self.blob_service_client:
                logger.warning("Azure Blob Storage not configured, using mock file URL")
                # Return a mock file URL when Azure Storage is not configured
                file_extension = Path(filename).suffix
                mock_blob_name = f"{conversation_id}/{uuid.uuid4()}{file_extension}"
                return f"https://mock-storage.blob.core.windows.net/{self.settings.AZURE_STORAGE_CONTAINER_NAME}/{mock_blob_name}"
                
            # Generate unique blob name
            file_extension = Path(filename).suffix
            blob_name = f"{conversation_id}/{uuid.uuid4()}{file_extension}"
            
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.settings.AZURE_STORAGE_CONTAINER_NAME,
                blob=blob_name
            )
            
            # Upload file
            blob_client.upload_blob(file_content, overwrite=True)
            
            # Return the blob URL
            return blob_client.url
            
        except Exception as e:
            logger.error(f"Error uploading file to blob storage: {e}")
            raise
    
    async def _extract_document_data(
        self, 
        file_content: bytes, 
        filename: str, 
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract data from document file.
        
        In a real implementation, this would use OCR and AI to extract data.
        For now, we'll use sample data based on the document type.
        """
        try:
            # Auto-detect document type if not provided
            if not document_type:
                document_type = self._detect_document_type(filename, file_content)
            
            # Get schema for this document type
            schema = get_document_schema(document_type)
            if not schema:
                logger.warning(f"No schema found for document type: {document_type}")
                # Use default schema
                schema = get_document_schema("بيانات صحيفة الدعوى")
            
            # Extract data based on schema
            extracted_data = await self._extract_data_by_schema(schema, file_content, filename)
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting document data: {e}")
            raise
    
    def _detect_document_type(self, filename: str, file_content: bytes) -> str:
        """Detect document type based on filename and content."""
        # Simple detection based on filename patterns
        filename_lower = filename.lower()
        
        if any(keyword in filename_lower for keyword in ["دعوى", "claim", "statement"]):
            return "بيانات صحيفة الدعوى"
        elif any(keyword in filename_lower for keyword in ["عقد", "contract", "agreement"]):
            return "عقد"
        elif any(keyword in filename_lower for keyword in ["شهادة", "certificate", "license"]):
            return "شهادة"
        else:
            # Default to statement of claim
            return "بيانات صحيفة الدعوى"
    
    async def _extract_data_by_schema(self, schema: DocumentSchema, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract data according to the document schema."""
        try:
            # In a real implementation, this would use OCR and AI
            # For now, we'll generate sample data based on the schema
            
            extracted_fields = []
            
            # Generate sample data for each field in the schema
            for field_def in schema.all_fields:
                sample_value = self._generate_sample_value(field_def)
                
                field_data = {
                    "field_name": field_def.name,
                    "field_name_arabic": field_def.arabic_name,
                    "field_value": sample_value,
                    "confidence": 0.95 if field_def.is_required else 0.85,
                    "page_number": 1,
                    "bounding_box": None,
                    "field_type": field_def.field_type,
                    "is_required": field_def.is_required,
                    "validation_rules": field_def.validation_rules
                }
                
                extracted_fields.append(field_data)
            
            return {
                "document_id": "extracted",
                "document_type": schema.document_type,
                "extracted_fields": extracted_fields,
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "total_pages": 1,
                "processing_status": "completed",
                "raw_text": f"محتوى النص المستخرج من الملف {filename}..."
            }
            
        except Exception as e:
            logger.error(f"Error extracting data by schema: {e}")
            raise
    
    def _generate_sample_value(self, field_def: Any) -> str:
        """Generate sample value for a field based on its type and requirements."""
        field_type = field_def.field_type
        is_required = field_def.is_required
        
        if not is_required:
            return "غير مذكور"
        
        # Generate sample values based on field type
        if field_type == "number":
            return "١٣٨٣٩٥١"
        elif field_type == "date":
            return "١٤٤٤/٠٣/١٩"
        elif field_type == "phone":
            return "٠٥٤٨٠٠٦٧٠٠"
        elif field_type == "email":
            return "example@email.com"
        elif field_type == "text":
            # Generate appropriate text based on field name
            if "case_number" in field_def.name:
                return "١٣٨٣٩٥١"
            elif "plaintiff" in field_def.name:
                return "اسم المدعي"
            elif "defendant" in field_def.name:
                return "اسم المدعى عليه"
            elif "court" in field_def.name:
                return "المحكمة الإدارية بالرياض"
            else:
                return "نص تجريبي"
        else:
            return "قيمة تجريبية"
    
    def _validate_document(self, extracted_data: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
        """Validate extracted document data."""
        try:
            document_type = extracted_data.get("document_type")
            if not document_type:
                return False, 0.0, ["Document type not specified"]
            
            return validate_document_data(document_type, extracted_data)
            
        except Exception as e:
            logger.error(f"Error validating document: {e}")
            return False, 0.0, [f"Validation error: {str(e)}"]
    
    async def get_document_metadata(self, file_url: str) -> Dict[str, Any]:
        """Get metadata for a document file."""
        try:
            # Parse blob URL
            from urllib.parse import urlparse
            parsed_url = urlparse(file_url)
            path_parts = parsed_url.path.strip('/').split('/')
            
            if len(path_parts) < 2:
                return {"size": None, "content_type": "application/pdf"}
            
            container_name = path_parts[0]
            blob_name = '/'.join(path_parts[1:])
            
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(container_name, blob_name)
            
            # Get blob properties
            blob_properties = blob_client.get_blob_properties()
            
            return {
                "size": blob_properties.size,
                "content_type": blob_properties.content_settings.content_type or "application/pdf",
                "last_modified": blob_properties.last_modified,
                "etag": blob_properties.etag
            }
            
        except Exception as e:
            logger.error(f"Error getting document metadata: {e}")
            return {"size": None, "content_type": "application/pdf"}
    
    async def stream_document_content(self, file_url: str) -> Tuple[Any, str, Dict[str, str]]:
        """Get streaming content and headers for a document."""
        try:
            # Parse blob URL
            from urllib.parse import urlparse
            parsed_url = urlparse(file_url)
            path_parts = parsed_url.path.strip('/').split('/')
            
            if len(path_parts) < 2:
                raise ValueError("Invalid blob URL format")
            
            container_name = path_parts[0]
            blob_name = '/'.join(path_parts[1:])
            
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(container_name, blob_name)
            
            # Get blob properties
            blob_properties = blob_client.get_blob_properties()
            
            # Determine content type and filename
            content_type = blob_properties.content_settings.content_type or "application/pdf"
            filename = Path(blob_name).name
            
            # Create streaming generator
            async def content_generator():
                try:
                    download_stream = blob_client.download_blob()
                    async for chunk in download_stream.chunks():
                        yield chunk
                except Exception as e:
                    logger.error(f"Error streaming document content: {e}")
                    raise
            
            # Prepare headers
            headers = {
                "Content-Disposition": f"inline; filename={filename}",
                "Cache-Control": "no-cache"
            }
            
            return content_generator(), content_type, headers
            
        except Exception as e:
            logger.error(f"Error streaming document content: {e}")
            raise 