from typing import Dict, Optional, List
from enum import Enum
from app.schemas.conversation import ConversationStatus
from app.modules.prompt_manager.manager import PromptManager
import logging

logger = logging.getLogger(__name__)

class ConversationStatusManager:
    """Manages conversation status transitions and prompt selection."""
    
    def __init__(self):
        """Initialize the status manager."""
        self.prompt_manager = PromptManager()
        self._status_prompt_mapping = self._initialize_status_prompt_mapping()
    
    def _initialize_status_prompt_mapping(self) -> Dict[ConversationStatus, str]:
        """Initialize mapping between conversation statuses and prompt types."""
        return {
            ConversationStatus.WAITING_FOR_CLAIM: "waiting_for_claim",
            ConversationStatus.CLAIM_UPLOADED: "default",
            ConversationStatus.CLAIM_VALIDATED: "default",
            ConversationStatus.CLAIM_REJECTED: "default",
            ConversationStatus.WAITING_FOR_ATTACHMENTS: "waiting_for_attachments",
            ConversationStatus.CLAIM_DISCUSSION: "claim_discussion",
            ConversationStatus.CLAIM_DOCS_DISCUSSION: "claim_docs_discussion",
            ConversationStatus.LEGAL_BASIS: "legal_basis",
            ConversationStatus.RESPONSE_DRAFTING: "default",
            ConversationStatus.RESPONSE_COMPLETED: "default",
            ConversationStatus.CLOSED: "default",
        }
    
    def get_prompt_for_status(self, status: ConversationStatus) -> Optional[str]:
        """
        Get the appropriate prompt for a given conversation status.
        
        Args:
            status: The current conversation status
            
        Returns:
            The prompt text or None if not found
        """
        try:
            prompt_type = self._status_prompt_mapping.get(status, "default")
            prompt = self.prompt_manager.get_prompt("chat", prompt_type)
            
            if not prompt:
                logger.warning(f"No prompt found for status {status}, falling back to default")
                prompt = self.prompt_manager.get_prompt("chat", "default")
            
            return prompt
            
        except Exception as e:
            logger.error(f"Error getting prompt for status {status}: {str(e)}")
            # Fallback to default prompt
            return self.prompt_manager.get_prompt("chat", "default")
    
    def reload_prompts(self):
        """Force reload all prompts."""
        self.prompt_manager.reload_prompts()
        logger.info("Prompts reloaded in status manager")
    
    def get_available_transitions(self, current_status: ConversationStatus) -> List[ConversationStatus]:
        """
        Get available status transitions from the current status.
        
        Args:
            current_status: The current conversation status
            
        Returns:
            List of available status transitions
        """
        transitions = {
            ConversationStatus.WAITING_FOR_CLAIM: [
                ConversationStatus.CLAIM_UPLOADED,
                ConversationStatus.CLAIM_DISCUSSION,
                ConversationStatus.CLAIM_VALIDATED,
                ConversationStatus.CLOSED
            ],
            ConversationStatus.CLAIM_UPLOADED: [
                ConversationStatus.CLAIM_DISCUSSION,
                ConversationStatus.CLAIM_VALIDATED,
                ConversationStatus.CLAIM_REJECTED,
                ConversationStatus.CLOSED
            ],
            ConversationStatus.CLAIM_VALIDATED: [
                ConversationStatus.WAITING_FOR_ATTACHMENTS,
                ConversationStatus.CLAIM_DISCUSSION,
                ConversationStatus.CLAIM_DOCS_DISCUSSION,
                ConversationStatus.RESPONSE_DRAFTING,
                ConversationStatus.CLAIM_REJECTED,
                ConversationStatus.CLOSED
            ],
            ConversationStatus.CLAIM_REJECTED: [
                ConversationStatus.WAITING_FOR_CLAIM,
                ConversationStatus.CLOSED
            ],
            ConversationStatus.WAITING_FOR_ATTACHMENTS: [
                ConversationStatus.CLAIM_VALIDATED,
                ConversationStatus.CLAIM_DISCUSSION,
                ConversationStatus.CLAIM_DOCS_DISCUSSION,
                ConversationStatus.LEGAL_BASIS,
                ConversationStatus.RESPONSE_DRAFTING,
                ConversationStatus.CLOSED
            ],
            ConversationStatus.CLAIM_DISCUSSION: [
                ConversationStatus.WAITING_FOR_ATTACHMENTS,
                ConversationStatus.CLAIM_DOCS_DISCUSSION,
                ConversationStatus.LEGAL_BASIS,
                ConversationStatus.RESPONSE_DRAFTING,
                ConversationStatus.CLOSED
            ],
            ConversationStatus.CLAIM_DOCS_DISCUSSION: [
                ConversationStatus.LEGAL_BASIS,
                ConversationStatus.RESPONSE_DRAFTING,
                ConversationStatus.CLAIM_DISCUSSION,
                ConversationStatus.CLOSED
            ],
            ConversationStatus.LEGAL_BASIS: [
                ConversationStatus.RESPONSE_DRAFTING,
                ConversationStatus.CLAIM_DISCUSSION,
                ConversationStatus.CLOSED
            ],
            ConversationStatus.RESPONSE_DRAFTING: [
                ConversationStatus.RESPONSE_COMPLETED,
                ConversationStatus.CLAIM_DISCUSSION,
                ConversationStatus.CLAIM_DOCS_DISCUSSION,
                ConversationStatus.LEGAL_BASIS,
                ConversationStatus.CLOSED
            ],
            ConversationStatus.RESPONSE_COMPLETED: [
                ConversationStatus.CLOSED
            ],
            ConversationStatus.CLOSED: []  # No transitions from closed
        }
        
        return transitions.get(current_status, [])
    
    def can_transition_to(self, current_status: ConversationStatus, target_status: ConversationStatus) -> bool:
        """
        Check if a transition from current_status to target_status is valid.
        
        Args:
            current_status: The current conversation status
            target_status: The target conversation status
            
        Returns:
            True if transition is valid, False otherwise
        """
        # Allow idempotent updates (same status -> same status)
        if current_status == target_status:
            return True
        available_transitions = self.get_available_transitions(current_status)
        return target_status in available_transitions
    
    def get_status_description(self, status: ConversationStatus) -> str:
        """
        Get a human-readable description of a conversation status.
        
        Args:
            status: The conversation status
            
        Returns:
            Description of the status
        """
        descriptions = {
            ConversationStatus.WAITING_FOR_CLAIM: "في انتظار رفع صحيفة الدعوى",
            ConversationStatus.CLAIM_UPLOADED: "تم رفع صحيفة الدعوى",
            ConversationStatus.CLAIM_VALIDATED: "تم التحقق من صحة صحيفة الدعوى",
            ConversationStatus.CLAIM_REJECTED: "تم رفض صحيفة الدعوى",
            ConversationStatus.WAITING_FOR_ATTACHMENTS: "جمع المرفقات الداعمة أو الانتقال للمرحلة التالية",
            ConversationStatus.CLAIM_DISCUSSION: "نقاش تفصيلي حول محتوى صحيفة الدعوى",
            ConversationStatus.CLAIM_DOCS_DISCUSSION: "نقاش حول المرفقات وصحيفة الدعوى",
            ConversationStatus.RESPONSE_DRAFTING: "جاري إعداد لائحة الرد",
            ConversationStatus.RESPONSE_COMPLETED: "تم إكمال لائحة الرد",
            ConversationStatus.CLOSED: "المحادثة مغلقة"
        }
        
        return descriptions.get(status, "حالة غير معروفة")
    
    def get_next_recommended_status(self, current_status: ConversationStatus) -> Optional[ConversationStatus]:
        """
        Get the recommended next status based on the current status.
        
        Args:
            current_status: The current conversation status
            
        Returns:
            Recommended next status or None if no recommendation
        """
        recommendations = {
            ConversationStatus.WAITING_FOR_CLAIM: ConversationStatus.CLAIM_UPLOADED,
            ConversationStatus.CLAIM_UPLOADED: ConversationStatus.CLAIM_VALIDATED,
            ConversationStatus.CLAIM_VALIDATED: ConversationStatus.WAITING_FOR_ATTACHMENTS,
            ConversationStatus.WAITING_FOR_ATTACHMENTS: ConversationStatus.RESPONSE_DRAFTING,
            ConversationStatus.RESPONSE_DRAFTING: ConversationStatus.RESPONSE_COMPLETED,
        }
        
        return recommendations.get(current_status) 