"""
Storage Manager for Claim Extractor

This module handles file storage operations for the claim extractor,
including uploading files to Azure Blob Storage and managing file URLs.
"""

import logging
import uuid
from typing import Optional
from pathlib import Path
from datetime import datetime

from app.core.config.settings import get_settings
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages file storage operations for claim extraction."""
    
    def __init__(self):
        self.settings = get_settings()
        self.blob_service_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Azure Blob Storage client."""
        try:
            if self.settings.AZURE_STORAGE_CONNECTION_STRING:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    self.settings.AZURE_STORAGE_CONNECTION_STRING
                )
                logger.info("Storage Manager initialized successfully")
            else:
                logger.warning("Azure Storage connection string not configured")
        except Exception as e:
            logger.error(f"Failed to initialize Storage Manager: {e}")
    
    async def upload_file(
        self, 
        file_content: bytes, 
        filename: str,
        conversation_id: Optional[str] = None
    ) -> str:
        """
        Upload file to Azure Blob Storage.
        
        Args:
            file_content: Raw file content
            filename: Original filename
            conversation_id: Optional conversation ID for organization
            
        Returns:
            Blob URL of uploaded file
        """
        try:
            if not self.blob_service_client:
                logger.warning("Blob service client not available, returning mock URL")
                return self._generate_mock_url(filename, conversation_id)
            
            # Generate unique blob name
            blob_name = self._generate_blob_name(filename, conversation_id)
            
            # Get container client
            container_name = self.settings.AZURE_STORAGE_CONTAINER_NAME
            container_client = self.blob_service_client.get_container_client(container_name)
            
            # Ensure container exists
            await self._ensure_container_exists(container_client)
            
            # Get blob client
            blob_client = container_client.get_blob_client(blob_name)
            
            # Upload file
            blob_client.upload_blob(file_content, overwrite=True)
            
            # Get blob URL
            blob_url = blob_client.url
            
            logger.info(f"File uploaded successfully: {blob_url}")
            return blob_url
            
        except AzureError as e:
            logger.error(f"Azure Storage error: {e}")
            return self._generate_mock_url(filename, conversation_id)
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return self._generate_mock_url(filename, conversation_id)
    
    def _generate_blob_name(self, filename: str, conversation_id: Optional[str] = None) -> str:
        """Generate unique blob name for file."""
        try:
            # Get file extension
            file_extension = Path(filename).suffix
            
            # Generate unique ID
            unique_id = str(uuid.uuid4())
            
            # Create timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Build blob name
            if conversation_id:
                blob_name = f"claims/{conversation_id}/{timestamp}_{unique_id}{file_extension}"
            else:
                blob_name = f"claims/{timestamp}_{unique_id}{file_extension}"
            
            return blob_name
            
        except Exception as e:
            logger.error(f"Error generating blob name: {e}")
            return f"claims/{uuid.uuid4()}{Path(filename).suffix}"
    
    def _generate_mock_url(self, filename: str, conversation_id: Optional[str] = None) -> str:
        """Generate mock URL when storage is not available."""
        try:
            container_name = self.settings.AZURE_STORAGE_CONTAINER_NAME or "leg-files"
            blob_name = self._generate_blob_name(filename, conversation_id)
            
            mock_url = f"https://mock-storage.blob.core.windows.net/{container_name}/{blob_name}"
            logger.info(f"Generated mock URL: {mock_url}")
            
            return mock_url
            
        except Exception as e:
            logger.error(f"Error generating mock URL: {e}")
            return f"https://mock-storage.blob.core.windows.net/leg-files/{uuid.uuid4()}.pdf"
    
    async def _ensure_container_exists(self, container_client):
        """Ensure the container exists, create if it doesn't."""
        try:
            # Check if container exists
            container_properties = container_client.get_container_properties()
            logger.info(f"Container {container_client.container_name} exists")
            
        except AzureError as e:
            if "ContainerNotFound" in str(e):
                # Create container
                container_client.create_container()
                logger.info(f"Container {container_client.container_name} created")
            else:
                raise e
    
    async def get_file_metadata(self, blob_url: str) -> dict:
        """
        Get metadata for a file in blob storage.
        
        Args:
            blob_url: URL of the blob
            
        Returns:
            Dictionary containing file metadata
        """
        try:
            if not self.blob_service_client:
                return {"size": None, "content_type": "application/pdf"}
            
            # Parse blob URL
            blob_client = self.blob_service_client.get_blob_client(
                container=self.settings.AZURE_STORAGE_CONTAINER_NAME,
                blob=self._extract_blob_name_from_url(blob_url)
            )
            
            # Get blob properties
            properties = blob_client.get_blob_properties()
            
            return {
                "size": properties.size,
                "content_type": properties.content_settings.content_type or "application/pdf",
                "last_modified": properties.last_modified,
                "etag": properties.etag
            }
            
        except Exception as e:
            logger.error(f"Error getting file metadata: {e}")
            return {"size": None, "content_type": "application/pdf"}
    
    def _extract_blob_name_from_url(self, blob_url: str) -> str:
        """Extract blob name from blob URL."""
        try:
            # Remove base URL to get blob name
            base_url = f"https://{self.blob_service_client.account_name}.blob.core.windows.net/{self.settings.AZURE_STORAGE_CONTAINER_NAME}/"
            blob_name = blob_url.replace(base_url, "")
            return blob_name
            
        except Exception as e:
            logger.error(f"Error extracting blob name from URL: {e}")
            return ""
    
    async def delete_file(self, blob_url: str) -> bool:
        """
        Delete file from blob storage.
        
        Args:
            blob_url: URL of the blob to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            if not self.blob_service_client:
                logger.warning("Blob service client not available, cannot delete file")
                return False
            
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.settings.AZURE_STORAGE_CONTAINER_NAME,
                blob=self._extract_blob_name_from_url(blob_url)
            )
            
            # Delete blob
            blob_client.delete_blob()
            
            logger.info(f"File deleted successfully: {blob_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    async def list_files(self, conversation_id: Optional[str] = None, prefix: str = "claims/") -> list:
        """
        List files in blob storage.
        
        Args:
            conversation_id: Optional conversation ID to filter files
            prefix: Prefix to filter files
            
        Returns:
            List of file information
        """
        try:
            if not self.blob_service_client:
                logger.warning("Blob service client not available, cannot list files")
                return []
            
            # Get container client
            container_client = self.blob_service_client.get_container_client(
                self.settings.AZURE_STORAGE_CONTAINER_NAME
            )
            
            # Build prefix
            if conversation_id:
                search_prefix = f"{prefix}{conversation_id}/"
            else:
                search_prefix = prefix
            
            # List blobs
            files = []
            blobs = container_client.list_blobs(name_starts_with=search_prefix)
            
            for blob in blobs:
                files.append({
                    "name": blob.name,
                    "size": blob.size,
                    "last_modified": blob.last_modified,
                    "url": f"https://{self.blob_service_client.account_name}.blob.core.windows.net/{self.settings.AZURE_STORAGE_CONTAINER_NAME}/{blob.name}"
                })
            
            logger.info(f"Listed {len(files)} files")
            return files
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def is_storage_available(self) -> bool:
        """Check if storage is available."""
        return self.blob_service_client is not None
    
    def get_storage_info(self) -> dict:
        """Get storage configuration information."""
        return {
            "storage_available": self.is_storage_available(),
            "container_name": self.settings.AZURE_STORAGE_CONTAINER_NAME,
            "connection_string_configured": bool(self.settings.AZURE_STORAGE_CONNECTION_STRING)
        } 