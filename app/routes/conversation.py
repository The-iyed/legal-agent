from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.modules.conversation.service import ConversationService
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationResponse, ConversationList, PaginatedConversationResponse, ConversationStatus
from bson import ObjectId
import logging
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    responses={
        400: {"description": "Bad Request - Invalid input data"},
        404: {"description": "Conversation not found"},
        500: {"description": "Internal server error"}
    }
)

def get_conversation_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> ConversationService:
    """Get conversation service instance."""
    return ConversationService(db)

@router.post(
    "/",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
    description="""
    Create a new conversation for a user.
    
    This endpoint creates a new conversation with the default status "waiting_for_claim".
    
    Required fields:
    - name: Name of the conversation
    - user_id: ID of the user creating the conversation
    
    Returns:
    - Conversation details including ID, name, user_id, status, and creation timestamp
    """
)
async def create_conversation(
    conversation: ConversationCreate = Body(
        ...,
        example={
            "name": "New Legal Consultation",
            "user_id": "user123"
        }
    ),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Create a new conversation.
    
    Args:
        conversation: The conversation creation data
        conversation_service: Service for managing conversations
        
    Returns:
        ConversationResponse: The created conversation
        
    Raises:
        HTTPException: 
            - 400: If the input data is invalid
            - 500: If there's an error creating the conversation
    """
    try:
        result = await conversation_service.create_conversation(conversation)
        return result
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}"
        )

@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get a conversation by ID",
    description="""
    Retrieve a conversation by its ID.
    
    Path Parameters:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    
    Returns:
    - Conversation details if found
    """
)
async def get_conversation(
    conversation_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Get a conversation by ID.
    
    Args:
        conversation_id: The conversation ID to retrieve
        conversation_service: Service for managing conversations
        
    Returns:
        Conversation details or null if not found
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid
            - 404: If the conversation doesn't exist
            - 500: If there's an error retrieving the conversation
    """
    try:
        # Validate conversation_id format
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format"
            )

        conversation = await conversation_service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return conversation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversation: {str(e)}"
        )

@router.put(
    "/{conversation_id}/status",
    response_model=ConversationResponse,
    summary="Update conversation status",
    description="""
    Update the status of a conversation.
    
    This endpoint allows updating the conversation status based on the conversation flow.
    Valid status transitions are enforced by the system.
    
    Path Parameters:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    
    Request Body:
    - status: New status for the conversation
    
    Returns:
    - Updated conversation details
    """
)
async def update_conversation_status(
    conversation_id: str,
    status_update: dict = Body(
        ...,
        example={
            "status": "claim_uploaded"
        }
    ),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Update conversation status.
    
    Args:
        conversation_id: The conversation ID to update
        status_update: The status update data
        conversation_service: Service for managing conversations
        
    Returns:
        Updated conversation details
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid or status transition is invalid
            - 404: If the conversation doesn't exist
            - 500: If there's an error updating the conversation
    """
    try:
        # Validate conversation_id format
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format"
            )

        # Validate status
        new_status_str = status_update.get("status")
        if not new_status_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status is required"
            )
        
        try:
            new_status = ConversationStatus(new_status_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {new_status_str}. Valid statuses: {[s.value for s in ConversationStatus]}"
            )

        # Update conversation status
        updated_conversation = await conversation_service.update_conversation_status(conversation_id, new_status)
        if not updated_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return updated_conversation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update conversation status: {str(e)}"
        )

@router.get(
    "/{conversation_id}/with-prompt",
    summary="Get conversation with prompt based on status",
    description="""
    Retrieve a conversation with its associated prompt based on the current status.
    
    This endpoint returns the conversation details along with the appropriate prompt
    that should be used for the current conversation stage.
    
    Path Parameters:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    
    Returns:
    - Conversation details with prompt and status information
    """
)
async def get_conversation_with_prompt(
    conversation_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Get conversation with prompt based on status.
    
    Args:
        conversation_id: The conversation ID to retrieve
        conversation_service: Service for managing conversations
        
    Returns:
        Conversation with prompt and status information
        
    Raises:
        HTTPException: 
            - 400: If the conversation_id is invalid
            - 404: If the conversation doesn't exist
            - 500: If there's an error retrieving the conversation
    """
    try:
        # Validate conversation_id format
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format"
            )

        conversation_data = await conversation_service.get_conversation_with_prompt(conversation_id)
        if not conversation_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return conversation_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation with prompt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversation with prompt: {str(e)}"
        )

@router.get(
    "/user/{user_id}",
    response_model=PaginatedConversationResponse,
    summary="Get all conversations for a user",
    description="""
    Retrieve all conversations for a specific user with pagination support.
    
    This endpoint returns a paginated list of conversations belonging to the specified user,
    including their current status and metadata.
    
    Path Parameters:
    - user_id: ID of the user whose conversations to retrieve
    
    Query Parameters:
    - page: Page number to retrieve (default: 1)
    - page_size: Number of conversations per page (default: 10, max: 100)
    
    Returns:
    - Paginated list of conversations with metadata
    """
)
async def get_user_conversations(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number to retrieve"),
    page_size: int = Query(10, ge=1, le=100, description="Number of conversations per page"),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Get all conversations for a user with pagination.
    
    Args:
        user_id: The user ID to retrieve conversations for
        page: Page number for pagination
        page_size: Number of conversations per page
        conversation_service: Service for managing conversations
        
    Returns:
        Paginated list of conversations
        
    Raises:
        HTTPException: 
            - 400: If pagination parameters are invalid
            - 500: If there's an error retrieving conversations
    """
    try:
        result = await conversation_service.get_user_conversations(user_id, page, page_size)
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving user conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user conversations: {str(e)}"
        )

@router.post(
    "/{conversation_id}/attachment-decision",
    response_model=ConversationResponse,
    summary="Handle user decision about uploading attachments",
    description="""
    Handle the user's decision about whether to upload supporting attachments for their validated claim.
    
    This endpoint allows users to:
    1. Accept and proceed to attachment upload phase
    2. Reject and skip directly to response drafting
    
    Path Parameters:
    - conversation_id: ID of the conversation (must be a valid MongoDB ObjectId)
    
    Request Body:
    - decision: "accept" to upload attachments, "reject" to skip
    - reason: Optional reason for the decision
    
    Returns:
    - Updated conversation details with new status
    """
)
async def handle_attachment_decision(
    conversation_id: str,
    decision_data: dict = Body(
        ...,
        example={
            "decision": "accept",
            "reason": "I have supporting documents to upload"
        }
    ),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    Handle user decision about uploading attachments.
    
    Args:
        conversation_id: The conversation ID
        decision_data: The decision data containing "decision" and optional "reason"
        conversation_service: Service for managing conversations
        
    Returns:
        Updated conversation details
        
    Raises:
        HTTPException: 
            - 400: If the decision is invalid or conversation is in wrong status
            - 404: If the conversation doesn't exist
            - 500: If there's an error processing the decision
    """
    try:
        # Validate conversation_id format
        if not ObjectId.is_valid(conversation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid conversation ID format"
            )
        
        decision = decision_data.get("decision")
        reason = decision_data.get("reason", "")
        
        if decision not in ["accept", "reject"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid decision. Must be 'accept' or 'reject'"
            )
        
        # Get current conversation to check status
        current_conversation = await conversation_service.get_conversation(conversation_id)
        if not current_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Check if conversation is in the right status
        if current_conversation.status != ConversationStatus.CLAIM_VALIDATED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Conversation must be in 'claim_validated' status. Current status: {current_conversation.status}"
            )
        
        # Determine new status based on decision
        if decision == "accept":
            new_status = ConversationStatus.WAITING_FOR_ATTACHMENTS
            logger.info(f"User accepted attachment upload for conversation {conversation_id}")
        else:  # reject
            new_status = ConversationStatus.RESPONSE_DRAFTING
            logger.info(f"User rejected attachment upload for conversation {conversation_id}")
        
        # Update conversation status
        result = await conversation_service.update_conversation_status(conversation_id, new_status)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update conversation status"
            )
        
        logger.info(f"Updated conversation {conversation_id} status to {new_status} based on attachment decision: {decision}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling attachment decision: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle attachment decision: {str(e)}"
        ) 