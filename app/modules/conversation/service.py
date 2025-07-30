from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
from typing import List, Optional
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationResponse, ConversationList, PaginatedConversationResponse, MetaData
import logging
import math

logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.conversations

    async def create_conversation(self, conversation: ConversationCreate) -> ConversationResponse:
        """Create a new conversation."""
        try:
            conversation_dict = conversation.model_dump()
            conversation_dict["created_at"] = datetime.utcnow()
            
            result = await self.collection.insert_one(conversation_dict)
            conversation_dict["_id"] = str(result.inserted_id)
            
            return ConversationResponse(**conversation_dict)
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            raise

    async def get_conversation(self, conversation_id: str) -> Optional[ConversationResponse]:
        """Get a conversation by ID."""
        try:
            if not ObjectId.is_valid(conversation_id):
                raise ValueError("Invalid conversation ID format")
            
            conversation = await self.collection.find_one({"_id": ObjectId(conversation_id)})
            if conversation:
                conversation["_id"] = str(conversation["_id"])
                return ConversationResponse(**conversation)
            return None
        except Exception as e:
            logger.error(f"Error getting conversation: {str(e)}")
            raise

    async def get_user_conversations(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 10
    ) -> PaginatedConversationResponse:
        """Get all conversations for a user with pagination."""
        try:
            total_conversations = await self.collection.count_documents({"user_id": user_id})
            
            # Calculate skip and limit for pagination
            skip = (page - 1) * page_size
            limit = page_size

            # Ensure limit is not negative
            if limit < 0:
                limit = 0
            
            cursor = self.collection.find({"user_id": user_id}).skip(skip).limit(limit).sort("created_at", 1)
            
            conversations = []
            async for conversation in cursor:
                conversation["_id"] = str(conversation["_id"])
                conversations.append(ConversationResponse(**conversation))
            
            total_pages = math.ceil(total_conversations / page_size) if page_size > 0 else 0

            return PaginatedConversationResponse(
                conversations=conversations,
                meta_data=MetaData(
                    total=total_conversations,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages
                )
            )
        except Exception as e:
            logger.error(f"Error getting user conversations: {str(e)}")
            raise

    async def update_conversation(
        self,
        conversation_id: str,
        conversation: ConversationUpdate
    ) -> Optional[ConversationResponse]:
        """Update a conversation."""
        try:
            if not ObjectId.is_valid(conversation_id):
                raise ValueError("Invalid conversation ID format")
            
            update_data = conversation.model_dump(exclude_unset=True)
            if not update_data:
                return None
            
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(conversation_id)},
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                result["_id"] = str(result["_id"])
                return ConversationResponse(**result)
            return None
        except Exception as e:
            logger.error(f"Error updating conversation: {str(e)}")
            raise

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        try:
            if not ObjectId.is_valid(conversation_id):
                raise ValueError("Invalid conversation ID format")
            
            result = await self.collection.delete_one({"_id": ObjectId(conversation_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting conversation: {str(e)}")
            raise 