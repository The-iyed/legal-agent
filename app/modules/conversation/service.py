from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
from typing import List, Optional
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationResponse, ConversationList, PaginatedConversationResponse, MetaData, ConversationStatus
from app.modules.conversation.status_manager import ConversationStatusManager
import logging
import math

logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.conversations
        self.status_manager = ConversationStatusManager()

    async def create_conversation(self, conversation: ConversationCreate) -> ConversationResponse:
        """Create a new conversation with default status."""
        try:
            conversation_dict = conversation.model_dump()
            conversation_dict["created_at"] = datetime.utcnow()
            # Ensure status is set to WAITING_FOR_CLAIM by default
            conversation_dict["status"] = ConversationStatus.WAITING_FOR_CLAIM
            
            result = await self.collection.insert_one(conversation_dict)
            conversation_dict["_id"] = str(result.inserted_id)
            
            logger.info(f"Created conversation {result.inserted_id} with status: {ConversationStatus.WAITING_FOR_CLAIM}")
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

    async def update_conversation_status(self, conversation_id: str, new_status: ConversationStatus) -> Optional[ConversationResponse]:
        """Update the status of a conversation."""
        try:
            if not ObjectId.is_valid(conversation_id):
                raise ValueError("Invalid conversation ID format")
            
            # Get current conversation
            current_conversation = await self.get_conversation(conversation_id)
            if not current_conversation:
                raise ValueError("Conversation not found")
            
            # Check if transition is valid
            if not self.status_manager.can_transition_to(current_conversation.status, new_status):
                raise ValueError(f"Invalid status transition from {current_conversation.status} to {new_status}")
            
            # Update status
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(conversation_id)},
                {"$set": {"status": new_status}},
                return_document=True
            )
            
            if result:
                result["_id"] = str(result["_id"])
                logger.info(f"Updated conversation {conversation_id} status from {current_conversation.status} to {new_status}")
                return ConversationResponse(**result)
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating conversation status: {str(e)}")
            raise

    async def get_conversation_with_prompt(self, conversation_id: str) -> Optional[dict]:
        """Get a conversation with its associated prompt based on status."""
        try:
            conversation = await self.get_conversation(conversation_id)
            if not conversation:
                return None
            
            # Get prompt for current status
            prompt = self.status_manager.get_prompt_for_status(conversation.status)
            
            return {
                "conversation": conversation,
                "prompt": prompt,
                "status_description": self.status_manager.get_status_description(conversation.status),
                "available_transitions": self.status_manager.get_available_transitions(conversation.status)
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation with prompt: {str(e)}")
            raise 