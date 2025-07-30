"""
Document Data Routes

This module handles retrieval of processed document data and metadata.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import logging
from typing import Optional, List

from app.core.database import get_database
from app.modules.conversation.service import ConversationService
from app.schemas.agent import StatementOfClaim

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["document-data"],
    responses={
        400: {"description": "Bad Request - Invalid input data"},
        404: {"description": "Document or conversation not found"},
        500: {"description": "Internal server error"}
    }
)


def get_conversation_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> ConversationService:
    """Get conversation service instance."""
    return ConversationService(db)


@router.get(
    "/statement-of-claim/{conversation_id}",
    summary="Get statement of claim data for a conversation",
    description="""
    Retrieve the statement of claim data associated with a conversation.
    
    This endpoint returns the processed document data including extracted fields,
    validation results, and file metadata.
    
    Path Parameters:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    
    Returns:
    - Statement of claim data if exists, null otherwise
    """
)
async def get_statement_of_claim(
    conversation_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Get statement of claim data for a conversation.
    
    Args:
        conversation_id: The conversation ID to retrieve data for
        conversation_service: Service for managing conversations
        
    Returns:
        Statement of claim data or null if not found
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid
            - 500: If there's an error retrieving the data
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

        # Retrieve statement of claim data
        statement_data = await _get_statement_of_claim_data(conversation_id)
        
        return statement_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving statement of claim: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statement of claim: {str(e)}"
        )


@router.get(
    "/{conversation_id}",
    summary="Get document data for a conversation",
    description="""
    Retrieve document data for any document type associated with a conversation.
    
    This endpoint returns the processed document data including extracted fields,
    validation results, and file metadata for any document type.
    
    Path Parameters:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    
    Returns:
    - Document data if exists, null otherwise
    """
)
async def get_document_data(
    conversation_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Get document data for a conversation.
    
    Args:
        conversation_id: The conversation ID to retrieve data for
        conversation_service: Service for managing conversations
        
    Returns:
        Document data or null if not found
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid
            - 500: If there's an error retrieving the data
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

        # Retrieve document data
        document_data = await _get_document_data(conversation_id)
        
        return document_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document data: {str(e)}"
        )


@router.get(
    "/{conversation_id}/fields",
    summary="Get extracted fields for a conversation",
    description="""
    Retrieve only the extracted fields from a document associated with a conversation.
    
    This endpoint returns just the extracted fields data without the full document metadata.
    
    Path Parameters:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    
    Returns:
    - Extracted fields data if exists, null otherwise
    """
)
async def get_extracted_fields(
    conversation_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Get extracted fields for a conversation.
    
    Args:
        conversation_id: The conversation ID to retrieve fields for
        conversation_service: Service for managing conversations
        
    Returns:
        Extracted fields data or null if not found
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid
            - 500: If there's an error retrieving the data
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

        # Retrieve extracted fields
        document_data = await _get_document_data(conversation_id)
        if not document_data:
            return None
        
        # Return only the extracted fields
        return {
            "conversation_id": conversation_id,
            "extracted_fields": document_data.get("extracted_fields", []),
            "document_type": document_data.get("document_type"),
            "validation_score": document_data.get("validation_score"),
            "is_valid": document_data.get("is_valid")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving extracted fields: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve extracted fields: {str(e)}"
        )


@router.get(
    "/{conversation_id}/validation",
    summary="Get validation results for a conversation",
    description="""
    Retrieve validation results for a document associated with a conversation.
    
    This endpoint returns validation information including score, errors, and validity status.
    
    Path Parameters:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    
    Returns:
    - Validation results if exists, null otherwise
    """
)
async def get_validation_results(
    conversation_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Get validation results for a conversation.
    
    Args:
        conversation_id: The conversation ID to retrieve validation for
        conversation_service: Service for managing conversations
        
    Returns:
        Validation results or null if not found
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid
            - 500: If there's an error retrieving the data
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

        # Retrieve validation results
        document_data = await _get_document_data(conversation_id)
        if not document_data:
            return None
        
        # Return only validation information
        return {
            "conversation_id": conversation_id,
            "document_type": document_data.get("document_type"),
            "validation_score": document_data.get("validation_score"),
            "is_valid": document_data.get("is_valid"),
            "validation_errors": document_data.get("validation_errors", []),
            "extracted_fields_count": len(document_data.get("extracted_fields", [])),
            "total_pages": document_data.get("total_pages", 1)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving validation results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve validation results: {str(e)}"
        )


# Helper functions
async def _get_statement_of_claim_data(conversation_id: str) -> Optional[dict]:
    """Get statement of claim data from the database."""
    from app.core.database import get_database
    db = get_database()
    
    try:
        statement = await db.statement_of_claim.find_one({"conversation_id": conversation_id})
        if statement:
            statement["_id"] = str(statement["_id"])
            return statement
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving statement of claim data: {e}")
        return None


async def _get_document_data(conversation_id: str) -> Optional[dict]:
    """Get document data from the database."""
    from app.core.database import get_database
    db = get_database()
    
    try:
        # Try to get from statement_of_claim collection first
        document = await db.statement_of_claim.find_one({"conversation_id": conversation_id})
        if document:
            document["_id"] = str(document["_id"])
            return document
        
        # If not found, could be extended to check other document collections
        # For now, return None
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving document data: {e}")
        return None 