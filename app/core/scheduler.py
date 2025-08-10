"""
FastAPI Scheduler for Background Tasks

This module provides scheduling functionality for background tasks using APScheduler.
It includes the conversation name generator that runs as a scheduled job.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from motor.motor_asyncio import AsyncIOMotorDatabase
from openai import AzureOpenAI
from bson import ObjectId

from app.core.database import get_database
from app.core.config.settings import Settings

logger = logging.getLogger(__name__)

class ConversationNameGenerator:
    """Service for automatically generating conversation names."""
    
    def __init__(self, db: AsyncIOMotorDatabase, settings: Settings):
        self.db = db
        self.settings = settings
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
    
    async def find_conversations_needing_names(self) -> List[Dict[str, Any]]:
        """
        Find conversations that need custom names generated.
        
        Criteria:
        - Have at least 5 messages
        - Name is still the default "New Conversation" or similar generic names
        - Haven't been updated in the last 5 minutes (to avoid conflicts)
        """
        try:
            generic_names = [
                "New Conversation", 
                "محادثة جديدة", 
                "Conversation", 
                "Chat"
            ]
            
            five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
            
            conversations_cursor = self.db.conversations.find({
                "$or": [
                    {"name": {"$in": generic_names}},
                    {"name": {"$regex": "^New Conversation", "$options": "i"}},
                    {"name": {"$regex": "^محادثة جديدة", "$options": "i"}}
                ],
                "created_at": {"$lt": five_minutes_ago}
            })
            
            conversations_needing_names = []
            
            async for conversation in conversations_cursor:
                conversation_id = str(conversation["_id"])
                
                message_count = await self.db.messages.count_documents({
                    "conversation_id": conversation_id
                })
                
                if message_count >= 5:
                    conversation["_id"] = conversation_id
                    conversation["message_count"] = message_count
                    conversations_needing_names.append(conversation)
                    logger.info(f"Found conversation {conversation_id} with {message_count} messages needing name")
            
            logger.info(f"Found {len(conversations_needing_names)} conversations needing names")
            return conversations_needing_names
            
        except Exception as e:
            logger.error(f"Error finding conversations needing names: {str(e)}")
            return []
    
    async def get_conversation_messages(self, conversation_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the first few messages from a conversation to generate a name."""
        try:
            messages_cursor = self.db.messages.find(
                {"conversation_id": conversation_id}
            ).sort("created_at", 1).limit(limit)
            
            messages = []
            async for message in messages_cursor:
                messages.append(message)
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages for conversation {conversation_id}: {str(e)}")
            return []
    
    def format_messages_for_llm(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages into a readable string for the LLM."""
        formatted_messages = []
        
        for i, message in enumerate(messages[:7]):  
            message_data = message.get("message_data", {})
            msg_type = message_data.get("type", "unknown")
            content = message_data.get("content", "")
            
            if msg_type == "user_message":
                formatted_messages.append(f"User: {content}")
            elif msg_type == "agent_response":
                formatted_messages.append(f"Assistant: {content}")
            else:
                formatted_messages.append(f"Message: {content}")
        
        return "\n".join(formatted_messages)
    
    async def generate_conversation_name(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """Generate a conversation name using OpenAI based on the messages."""
        try:
            if not messages:
                return None
            
            formatted_messages = self.format_messages_for_llm(messages)
            
            has_arabic = any('\u0600' <= char <= '\u06FF' for char in formatted_messages)
            
            if has_arabic:
                system_prompt = """أنت مساعد ذكي مختص في إنشاء عناوين للمحادثات.

قم بإنشاء عنوان مختصر وواضح للمحادثة بناءً على المحتوى المقدم.

المتطلبات:
- العنوان يجب أن يكون من 3-4 كلمات فقط
- يجب أن يلخص الموضوع الرئيسي للمحادثة
- استخدم اللغة العربية
- لا تستخدم علامات ترقيم في العنوان
- اجعل العنوان واضحاً ومفهوماً

أمثلة على عناوين جيدة:
- أسئلة عن التسويق الرقمي
- مشاكل الشبكة والحلول
- نصائح للطبخ المنزلي
- استفسارات قانونية عامة

قدم العنوان فقط بدون أي نص إضافي."""

                user_prompt = f"بناءً على المحادثة التالية، قم بإنشاء عنوان مناسب:\n\n{formatted_messages}"
            else:
                system_prompt = """You are an AI assistant specialized in creating conversation titles.

Generate a concise and clear title for the conversation based on the provided content.

Requirements:
- Title must be exactly 3-4 words
- Should summarize the main topic of the conversation
- Use Arabic language
- No punctuation marks in the title
- Make it clear and understandable

Examples of good titles:
- Digital Marketing Questions
- Network Issues Solutions
- Home Cooking Tips
- General Legal Inquiries

Provide only the title without any additional text."""

                user_prompt = f"Based on the following conversation, create an appropriate title:\n\n{formatted_messages}"
            
            messages_for_api = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=messages_for_api,
                max_tokens=20,
                temperature=0.0
            )
            
            generated_name = response.choices[0].message.content.strip()
            
            generated_name = generated_name.replace('"', '').replace("'", "").strip()
            
            word_count = len(generated_name.split())
            if word_count < 3 or word_count > 4:
                logger.warning(f"Generated name '{generated_name}' has {word_count} words, should be 3-4")
                if word_count > 4:
                    generated_name = " ".join(generated_name.split()[:4])
                elif word_count < 3:
                    return None
            
            logger.info(f"Generated conversation name: '{generated_name}'")
            return generated_name
            
        except Exception as e:
            logger.error(f"Error generating conversation name: {str(e)}")
            return None
    
    async def update_conversation_name(self, conversation_id: str, new_name: str) -> bool:
        """Update the conversation name in the database."""
        try:
            result = await self.db.conversations.update_one(
                {"_id": ObjectId(conversation_id)},
                {"$set": {"name": new_name}}
            )
            
            if result.modified_count > 0:
                logger.info(f"Successfully updated conversation {conversation_id} name to '{new_name}'")
                return True
            else:
                logger.warning(f"No conversation updated for ID {conversation_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating conversation {conversation_id} name: {str(e)}")
            return False
    
    async def process_conversation(self, conversation: Dict[str, Any]) -> bool:
        """Process a single conversation to generate and update its name."""
        try:
            conversation_id = conversation["_id"]
            current_name = conversation.get("name", "")
            
            logger.info(f"Processing conversation {conversation_id} (current name: '{current_name}')")
            
            # Get messages for this conversation
            messages = await self.get_conversation_messages(conversation_id, limit=10)
            
            if not messages:
                logger.warning(f"No messages found for conversation {conversation_id}")
                return False
            
            new_name = await self.generate_conversation_name(messages)
            
            if not new_name:
                logger.warning(f"Could not generate name for conversation {conversation_id}")
                return False
            
            success = await self.update_conversation_name(conversation_id, new_name)
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing conversation {conversation.get('_id', 'unknown')}: {str(e)}")
            return False
    
    async def run_name_generation_job(self):
        """Main job execution method for scheduled tasks."""
        try:
            logger.info("🤖 Starting conversation name generation job")
            
            conversations = await self.find_conversations_needing_names()
            
            if not conversations:
                logger.info("✅ No conversations found that need name updates")
                return
            
            success_count = 0
            total_count = len(conversations)
            
            for conversation in conversations:
                try:
                    success = await self.process_conversation(conversation)
                    if success:
                        success_count += 1
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing conversation {conversation.get('_id', 'unknown')}: {str(e)}")
                    continue
            
            logger.info(f"🎉 Conversation name generation completed: {success_count}/{total_count} successful updates")
            
        except Exception as e:
            logger.error(f"❌ Error in conversation name generation job: {str(e)}")


class TaskScheduler:
    """Main scheduler class for managing background tasks."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.db = None
        self.settings = Settings()
        self.conversation_name_generator = None
        
    async def initialize(self, db: AsyncIOMotorDatabase):
        """Initialize the scheduler with database connection."""
        self.db = db
        self.conversation_name_generator = ConversationNameGenerator(db, self.settings)
        
        # Disable automatic conversation name generation job per product requirement
        # self.scheduler.add_job(
        #     func=self.conversation_name_generator.run_name_generation_job,
        #     trigger=CronTrigger(minute="*/5"), 
        #     id="conversation_name_generation",
        #     name="Generate Conversation Names",
        #     replace_existing=True,
        #     max_instances=1  
        # )
        
        logger.info("📅 Task scheduler initialized (conversation name generation job disabled)")
    
    def start(self):
        """Start the scheduler."""
        try:
            # self.scheduler.start()
            logger.info("🚀 Task scheduler start skipped (no jobs enabled)")
        except Exception as e:
            logger.error(f"❌ Failed to start task scheduler: {str(e)}")
    
    def shutdown(self):
        """Shutdown the scheduler."""
        try:
            self.scheduler.shutdown()
            logger.info("🛑 Task scheduler shutdown successfully")
        except Exception as e:
            logger.error(f"❌ Error shutting down task scheduler: {str(e)}")
    
    def get_jobs(self):
        """Get list of scheduled jobs."""
        return self.scheduler.get_jobs()
    
    async def trigger_name_generation_now(self):
        """Manually trigger conversation name generation (for testing/admin)."""
        if self.conversation_name_generator:
            await self.conversation_name_generator.run_name_generation_job()
        else:
            logger.error("❌ Conversation name generator not initialized")

# Global scheduler instance
task_scheduler = TaskScheduler() 