from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
import logging

logger = logging.getLogger(__name__)

class SummarizationAgent(BaseAgent):
    """Agent for handling text summarization tasks."""
    
    async def _process_query(self, messages: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Process a summarization query using Azure OpenAI.
        
        Args:
            messages: Pre-prepared messages for the API
            
        Returns:
            The summarized text
        """
        completion = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages
        )
        
        response = completion.choices[0].message.content
        logger.info(f"Received response from OpenAI: {response[:100]}...")
        return response
    
    @property
    def agent_type(self) -> str:
        """Get the type of this agent."""
        return "summarization" 