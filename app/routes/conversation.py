from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List
from app.core.database import get_database
from app.core.auth import get_current_user
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationList,
    PaginatedConversationResponse
)
from app.modules.conversation.service import ConversationService
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    responses={
        400: {"description": "Bad Request - Invalid input data"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
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
    description="Create a new conversation. No authentication required."
)
async def create_conversation(
    conversation: ConversationCreate,
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    try:
        return await conversation_service.create_conversation(conversation)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversation: {str(e)}"
        )

@router.get(
    "/user/{user_id}",
    response_model=PaginatedConversationResponse,
    summary="Get all conversations for a user",
    description="Get all conversations for a specific user with pagination support."
)
async def get_user_conversations(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number to retrieve"),
    page_size: int = Query(10, ge=1, le=100, description="Number of conversations per page"),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    try:
        return await conversation_service.get_user_conversations(user_id, page, page_size)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversations: {str(e)}"
        )

@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Update a conversation",
    description="Update an existing conversation by its ID."
)
async def update_conversation(
    conversation_id: str,
    conversation_update: ConversationUpdate,
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    try:
        updated_conversation = await conversation_service.update_conversation(conversation_id, conversation_update)
        if not updated_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        return updated_conversation
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update conversation: {str(e)}"
        )

@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
    description="Delete a conversation by its ID."
)
async def delete_conversation(
    conversation_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    try:
        deleted = await conversation_service.delete_conversation(conversation_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        ) 