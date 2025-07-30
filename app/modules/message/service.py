from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
from typing import List, Optional
from app.schemas.message import MessageCreate, MessageResponse, MessageList, PaginatedMessageResponse
import logging
import math

logger = logging.getLogger(__name__)

class MessageService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.messages

    async def create_message(self, message: MessageCreate) -> MessageResponse:
        """Create a new message."""
        try:
            message_dict = message.model_dump()
            message_dict["created_at"] = datetime.utcnow()
            
            result = await self.collection.insert_one(message_dict)
            message_dict["_id"] = str(result.inserted_id)
            
            return MessageResponse(**message_dict)
        except Exception as e:
            logger.error(f"Error creating message: {str(e)}")
            raise

    async def get_full_conversation_history(self, conversation_id: str) -> List[dict]:
        """Retrieve the full conversation history for a given conversation ID, ordered by creation time."""
        try:
            if not ObjectId.is_valid(conversation_id):
                logger.warning(f"MessageService: Invalid conversation ID format: {conversation_id}")
                raise ValueError("Invalid conversation ID format")
            
            logger.info(f"MessageService: Fetching full conversation history for conversation ID: {conversation_id} from DB.")
            query = {"conversation_id": conversation_id}
            logger.info(f"MessageService: Using query: {query}")
            
            # First, check if any messages exist
            count = await self.collection.count_documents(query)
            logger.info(f"MessageService: Found {count} messages for conversation ID: {conversation_id}")
            
            if count == 0:
                logger.warning(f"MessageService: No messages found for conversation ID: {conversation_id}")
                return []
            
            cursor = self.collection.find(query).sort("created_at", 1)
            history = []
            async for message in cursor:
                message["_id"] = str(message["_id"])
                logger.debug(f"MessageService: Retrieved message: {message}")
                history.append(message)
            
            logger.info(f"MessageService: Retrieved {len(history)} messages for conversation ID: {conversation_id} from DB.")
            if len(history) > 0:
                logger.info(f"MessageService: First message content: {history[0].get('message_data', {}).get('content', 'No content')}")
                logger.info(f"MessageService: Last message content: {history[-1].get('message_data', {}).get('content', 'No content')}")
            
            return history
        except Exception as e:
            logger.error(f"Error getting full conversation history for {conversation_id}: {str(e)}")
            raise

    async def get_conversation_messages(
        self,
        conversation_id: str,
        page: int = 1,
        page_size: int = 50
    ) -> PaginatedMessageResponse:
        """Get all messages for a conversation with pagination."""
        try:
            if not ObjectId.is_valid(conversation_id):
                raise ValueError("Invalid conversation ID format")
            
            total_messages = await self.collection.count_documents({"conversation_id": conversation_id})
            
            # Calculate skip and limit for pagination
            skip = (page - 1) * page_size
            limit = page_size

            # Ensure limit is not negative
            if limit < 0:
                limit = 0
            
            cursor = self.collection.find({"conversation_id": conversation_id}).skip(skip).limit(limit).sort("created_at", 1)
            
            messages = []
            async for message in cursor:
                message["_id"] = str(message["_id"])
                messages.append(MessageResponse(**message))
            
            total_pages = math.ceil(total_messages / page_size) if page_size > 0 else 0

            return PaginatedMessageResponse(
                messages=messages,
                meta_data={
                    "total": total_messages,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages
                }
            )
        except Exception as e:
            logger.error(f"Error getting conversation messages: {str(e)}")
            raise 