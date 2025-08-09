from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.database import get_database
from app.schemas.message import MessageCreate, MessageResponse, MessageList, PaginatedMessageResponse
from app.modules.message.service import MessageService
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(
    prefix="/messages",
    tags=["messages"],
    responses={
        400: {"description": "Bad Request - Invalid input data"},
        404: {"description": "Conversation not found"},
        500: {"description": "Internal server error"}
    }
)

def get_message_service(db: AsyncIOMotorDatabase = Depends(get_database)) -> MessageService:
    """Get message service instance."""
    return MessageService(db)

@router.post(
    "/",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new message",
    description="Create a new message in a conversation."
)
async def create_message(
    message: MessageCreate,
    message_service: MessageService = Depends(get_message_service)
):
    try:
        return await message_service.create_message(message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create message: {str(e)}"
        )

@router.get(
    "/conversation/{conversation_id}",
    response_model=PaginatedMessageResponse,
    summary="Get all messages for a conversation",
    description="Get all messages for a specific conversation with pagination support."
)
async def get_conversation_messages(
    conversation_id: str,
    page: int = Query(1, ge=1, description="Page number to retrieve"),
    page_size: int = Query(50, ge=1, le=100, description="Number of messages per page"),
    newest_first: bool = Query(False, description="Return newest messages first if true"),
    message_service: MessageService = Depends(get_message_service)
):
    try:
        return await message_service.get_conversation_messages(conversation_id, page, page_size, sort_desc=newest_first)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve messages: {str(e)}"
        ) 