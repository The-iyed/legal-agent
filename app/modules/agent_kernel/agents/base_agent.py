from typing import Dict, Any, Optional, List
from openai import AzureOpenAI
from ....core.config import settings, Settings
import logging

logger = logging.getLogger(__name__)


class BaseAgent:

    def __init__(self, settings: Settings = settings):
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME

    async def execute(
        self, query: str, prompt: str, context: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        try:
            messages = await self._prepare_messages(query, prompt, context)
            response = await self._process_query(messages)

            return {
                "response": response,
                "agent_type": self.agent_type,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error in agent execution: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "agent_type": self.agent_type,
                "status": "error"
            }

    async def _prepare_messages(self, query: str, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, str]]:

        messages = [{"role": "system", "content": prompt}]
        
        if context is not None:
            logger.info(
                f"{self.agent_type}Agent: Received context with {len(context)} messages.")
            for i, msg in enumerate(context):
                content = msg.get("message_data", {}).get("content", "N/A")
                msg_type = msg.get("message_data", {}).get("type", "unknown")
                logger.info(
                    f"{self.agent_type}Agent Context Message {i+1}: Type={msg_type}, Content={content[:100]}...")
        else:
            logger.info(f"{self.agent_type}Agent: Received no context.")

        if context:
            for msg in context:
                msg_type = msg.get("message_data", {}).get("type", "")
                content = msg.get("message_data", {}).get("content", "")

                if msg_type == "user_message":
                    messages.append({"role": "user", "content": content})
                    logger.debug(
                        f"Added user message to context: {content[:50]}...")
                elif msg_type == "agent_response":
                    messages.append({"role": "assistant", "content": content})
                    logger.debug(
                        f"Added agent response to context: {content[:50]}...")

        messages.append({"role": "user", "content": query})
        logger.info(f"Added current query to messages: {query[:50]}...")

        logger.info(f"Total messages being sent to OpenAI: {len(messages)}")
        return messages

    async def _process_query(self, messages: Optional[List[Dict[str, str]]] = None) -> str:

        raise NotImplementedError("Subclasses must implement _process_query")

    @property
    def agent_type(self) -> str:
        raise NotImplementedError("Subclasses must implement agent_type")
