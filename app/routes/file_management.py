"""
File Management Routes

This module handles all file-related operations including upload, download,
and file information retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import logging
from typing import Optional

from app.core.database import get_database
from app.modules.document_processor.service import DocumentProcessorService
from app.modules.response_generator.service import ResponseGeneratorService
from app.modules.conversation.service import ConversationService
from app.modules.message.service import MessageService
from app.modules.claim_extractor.service import ClaimExtractorService
from app.schemas.agent import FileUploadResponse, FileInfoResponse
from app.schemas.message import MessageCreate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/files",
    tags=["file-management"],
    responses={
        400: {"description": "Bad Request - Invalid input data"},
        404: {"description": "File or conversation not found"},
        500: {"description": "Internal server error"}
    }
)


def get_document_processor_service() -> DocumentProcessorService:
    """Get document processor service instance."""
    return DocumentProcessorService()


def get_response_generator_service() -> ResponseGeneratorService:
    """Get response generator service instance."""
    return ResponseGeneratorService()


def get_conversation_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> ConversationService:
    """Get conversation service instance."""
    return ConversationService(db)


def get_message_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> MessageService:
    """Get message service instance."""
    return MessageService(db)


def get_claim_extractor_service() -> ClaimExtractorService:
    """Get claim extractor service instance."""
    return ClaimExtractorService()


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    summary="Upload and process legal document files",
    description="""
    Upload a legal document file for processing and validation.
    
    This endpoint:
    1. Validates that the conversation exists
    2. Uploads the file to Azure Blob Storage
    3. Extracts and validates document data against configured schemas
    4. Stores the processed data in the database if valid
    5. Returns processing results with Arabic response
    
    Required fields:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    - user_id: ID of the user uploading the file
    - file: The document file to upload (PDF, image, etc.)
    
    Returns:
    - response: Arabic response message about processing results
    - file_url: URL of the uploaded file in blob storage
    - case_number: Extracted case number if valid
    - is_valid: Whether the document is valid
    - metadata: Additional processing information
    """
)
async def upload_file(
    conversation_id: str = Form(..., description="Conversation ID"),
    user_id: str = Form(..., description="User ID"),
    file: UploadFile = File(..., description="Document file to upload"),
    document_processor: DocumentProcessorService = Depends(get_document_processor_service),
    response_generator: ResponseGeneratorService = Depends(get_response_generator_service),
    conversation_service: ConversationService = Depends(get_conversation_service),
    message_service: MessageService = Depends(get_message_service),
    claim_extractor: ClaimExtractorService = Depends(get_claim_extractor_service)
):
    """
    Upload and process a legal document file.
    
    Args:
        conversation_id: The conversation ID to associate the file with
        user_id: The user ID uploading the file
        file: The document file to upload and process
        document_processor: Service for processing files
        response_generator: Service for generating responses
        conversation_service: Service for managing conversations
        message_service: Service for managing messages
        
    Returns:
        FileUploadResponse: Processing results and metadata
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid or file is invalid
            - 404: If the conversation doesn't exist
            - 500: If there's an error processing the file
    """
    try:
        # Validate conversation_id format
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format"
            )

        # Verify conversation exists
        conversation = await conversation_service.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )

        # Check file size (limit to 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size too large. Maximum size is 10MB."
            )

        # Process document with enhanced claim extraction
        extracted_data = await document_processor.process_document(
            file_content=file_content,
            filename=file.filename,
            conversation_id=conversation_id
        )

        # Enhanced claim extraction using the new service
        claim_extraction_result = await claim_extractor.extract_claim_from_pdf(
            file_content=file_content,
            filename=file.filename,
            conversation_id=conversation_id
        )

        # Merge extracted data with claim extraction results
        enhanced_data = await _merge_extraction_results(extracted_data, claim_extraction_result)

        # Store enhanced document data in database
        await _store_document_data(conversation_id, enhanced_data)

        # Store user message about file upload
        await _store_file_upload_message(file.filename, conversation_id, user_id, message_service)

        # Generate enhanced response using claim extraction results
        context = response_generator.create_response_context(
            conversation_id=conversation_id,
            user_id=user_id,
            extracted_data=enhanced_data,
            filename=file.filename
        )
        
        # Use refined response from claim extraction if available
        if claim_extraction_result.refined_response:
            response_text = claim_extraction_result.refined_response
        else:
            response_text = response_generator.generate_file_upload_response(context)

        # Store agent response
        await _store_agent_response(conversation_id, user_id, response_text, message_service)

        # Prepare enhanced response
        case_number = claim_extraction_result.extracted_claim.case_number if claim_extraction_result.extracted_claim else None
        
        return FileUploadResponse(
            response=response_text,
            file_url=enhanced_data.get("file_url"),
            case_number=case_number,
            is_valid=claim_extraction_result.extracted_claim.is_valid if claim_extraction_result.extracted_claim else False,
            metadata={
                "document_type": enhanced_data.get("document_type"),
                "validation_score": claim_extraction_result.extracted_claim.processing_confidence if claim_extraction_result.extracted_claim else 0.0,
                "validation_errors": claim_extraction_result.extracted_claim.validation_errors if claim_extraction_result.extracted_claim else [],
                "total_pages": enhanced_data.get("total_pages", 1),
                "processing_id": claim_extraction_result.processing_id,
                "processing_time": claim_extraction_result.processing_time,
                "document_intelligence_confidence": claim_extraction_result.document_intelligence_confidence,
                "openai_confidence": claim_extraction_result.openai_confidence,
                "extraction_status": claim_extraction_result.status.value
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(e)}"
        )


@router.get(
    "/{conversation_id}",
    response_model=FileInfoResponse,
    summary="Get file information and download link for a conversation",
    description="""
    Retrieve file information and generate a secure download link for documents uploaded in a conversation.
    
    This endpoint:
    1. Validates that the conversation exists
    2. Retrieves the document data
    3. Generates a secure download link for the file
    4. Returns file metadata and access information
    
    Path Parameters:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    
    Returns:
    - File information including download link, metadata, and access details
    """
)
async def get_file_info(
    conversation_id: str,
    document_processor: DocumentProcessorService = Depends(get_document_processor_service),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Get file information and download link for a conversation.
    
    Args:
        conversation_id: The conversation ID to retrieve file info for
        document_processor: Service for retrieving document data
        conversation_service: Service for managing conversations
        
    Returns:
        FileInfoResponse: File information with download link and metadata
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid
            - 404: If the conversation or file doesn't exist
            - 500: If there's an error retrieving the file info
    """
    try:
        # Validate conversation_id format
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format"
            )

        # Verify conversation exists
        conversation = await conversation_service.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Get document data
        document_data = await _get_document_data(conversation_id)
        if not document_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No file found for this conversation"
            )

        # Generate file info response
        file_info = await _generate_file_info_response(conversation_id, document_data, document_processor)
        
        return file_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving file info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve file info: {str(e)}"
        )


@router.get(
    "/{conversation_id}/download",
    summary="Download file directly",
    description="""
    Download the file directly from Azure Blob Storage.
    
    This endpoint:
    1. Validates the conversation exists
    2. Retrieves the file from Azure Blob Storage
    3. Streams the file content to the client
    
    Path Parameters:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    
    Returns:
    - File content as a stream with appropriate headers
    """
)
async def download_file(
    conversation_id: str,
    document_processor: DocumentProcessorService = Depends(get_document_processor_service),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Download file directly from Azure Blob Storage.
    
    Args:
        conversation_id: The conversation ID to download file for
        document_processor: Service for retrieving and streaming files
        conversation_service: Service for managing conversations
        
    Returns:
        File content stream
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid
            - 404: If the conversation or file doesn't exist
            - 500: If there's an error downloading the file
    """
    try:
        # Validate conversation_id format
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format"
            )

        # Verify conversation exists
        conversation = await conversation_service.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Get document data
        document_data = await _get_document_data(conversation_id)
        if not document_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No file found for this conversation"
            )

        # Stream file content
        file_url = document_data.get("file_url")
        if not file_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File URL not found"
            )

        content_generator, content_type, headers = await document_processor.stream_document_content(file_url)
        
        # Add custom headers
        headers.update({
            "X-Conversation-ID": conversation_id,
            "X-Case-Number": document_data.get("case_number", "")
        })
        
        return StreamingResponse(
            content_generator,
            media_type=content_type,
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )


# Helper functions
async def _merge_extraction_results(extracted_data: dict, claim_extraction_result) -> dict:
    """Merge original extraction data with enhanced claim extraction results."""
    try:
        enhanced_data = extracted_data.copy()
        
        # Add claim extraction results
        if claim_extraction_result.extracted_claim:
            claim_dict = claim_extraction_result.extracted_claim.dict()
            enhanced_data["claim_info"] = claim_dict
            
            # Update existing fields with enhanced data
            for field, value in claim_dict.items():
                if value and value != "غير مذكور":
                    enhanced_data[field] = value
        
        # Add processing metadata
        enhanced_data["processing_id"] = claim_extraction_result.processing_id
        enhanced_data["processing_time"] = claim_extraction_result.processing_time
        enhanced_data["document_intelligence_confidence"] = claim_extraction_result.document_intelligence_confidence
        enhanced_data["openai_confidence"] = claim_extraction_result.openai_confidence
        enhanced_data["extraction_status"] = claim_extraction_result.status.value
        enhanced_data["refined_response"] = claim_extraction_result.refined_response
        
        # Update validation information
        if claim_extraction_result.extracted_claim:
            enhanced_data["is_valid"] = claim_extraction_result.extracted_claim.is_valid
            enhanced_data["validation_score"] = claim_extraction_result.extracted_claim.processing_confidence
            enhanced_data["validation_errors"] = claim_extraction_result.extracted_claim.validation_errors
        
        return enhanced_data
        
    except Exception as e:
        logger.error(f"Error merging extraction results: {e}")
        return extracted_data


async def _store_document_data(conversation_id: str, extracted_data: dict) -> None:
    """Store document data in the database."""
    from app.core.database import get_database
    db = get_database()
    
    try:
        # Store in statement_of_claim collection
        document_data = {
            "conversation_id": conversation_id,
            **extracted_data,
            "created_at": extracted_data.get("processing_timestamp"),
            "updated_at": extracted_data.get("processing_timestamp")
        }
        
        await db.statement_of_claim.insert_one(document_data)
        logger.info(f"Stored document data for conversation: {conversation_id}")
        
    except Exception as e:
        logger.error(f"Error storing document data: {e}")
        raise


async def _store_file_upload_message(
    filename: str, 
    conversation_id: str, 
    user_id: str, 
    message_service: MessageService
) -> None:
    """Store user message about file upload."""
    try:
        message_data = MessageCreate(
            conversation_id=conversation_id,
            user_id=user_id,
            content=f"تم رفع الملف: {filename}",
            message_type="user_message",
            query_type="file",
            metadata={
                "filename": filename,
                "upload_timestamp": "2025-07-28T21:42:31.621201"
            }
        )
        
        await message_service.create_message(message_data)
        logger.info(f"Stored file upload message for conversation: {conversation_id}")
        
    except Exception as e:
        logger.error(f"Error storing file upload message: {e}")
        raise


async def _store_agent_response(
    conversation_id: str, 
    user_id: str, 
    response_text: str, 
    message_service: MessageService
) -> None:
    """Store agent response message."""
    try:
        message_data = MessageCreate(
            conversation_id=conversation_id,
            user_id=user_id,
            content=response_text,
            message_type="agent_response",
            query_type="file",
            metadata={
                "file_processed": True,
                "agent_type": "file_processor"
            }
        )
        
        await message_service.create_message(message_data)
        logger.info(f"Stored agent response for conversation: {conversation_id}")
        
    except Exception as e:
        logger.error(f"Error storing agent response: {e}")
        raise


async def _get_document_data(conversation_id: str) -> Optional[dict]:
    """Get document data from the database."""
    from app.core.database import get_database
    db = get_database()
    
    try:
        document = await db.statement_of_claim.find_one({"conversation_id": conversation_id})
        if document:
            document["_id"] = str(document["_id"])
            return document
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving document data: {e}")
        return None


async def _generate_file_info_response(
    conversation_id: str, 
    document_data: dict, 
    document_processor: DocumentProcessorService
) -> FileInfoResponse:
    """Generate file info response."""
    try:
        file_url = document_data.get("file_url", "")
        if not file_url:
            raise ValueError("No file URL found in document data")
        
        # Get file metadata
        file_metadata = await document_processor.get_document_metadata(file_url)
        
        # Generate download URL
        import os
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        download_url = f"{base_url}/files/{conversation_id}/download"
        
        # Extract filename from URL
        from urllib.parse import urlparse
        from pathlib import Path
        parsed_url = urlparse(file_url)
        filename = Path(parsed_url.path).name
        if not filename:
            filename = f"document_{conversation_id}.pdf"
        
        # Extract case number
        case_number = None
        extracted_fields = document_data.get("extracted_fields", [])
        for field in extracted_fields:
            if field.get("field_name") == "case_number":
                case_number = field.get("field_value")
                break
        
        return FileInfoResponse(
            conversation_id=conversation_id,
            file_url=file_url,
            download_url=download_url,
            filename=filename,
            file_size=file_metadata.get("size"),
            content_type=file_metadata.get("content_type", "application/pdf"),
            upload_date=document_data.get("created_at"),
            case_number=case_number,
            document_type=document_data.get("document_type", ""),
            validation_score=document_data.get("validation_score", 0.0),
            is_valid=document_data.get("is_valid", False),
            total_pages=document_data.get("total_pages", 1),
            metadata={
                "extracted_fields_count": len(extracted_fields),
                "processing_status": document_data.get("processing_status", "unknown"),
                "validation_errors_count": len(document_data.get("validation_errors", []))
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating file info response: {e}")
        raise 