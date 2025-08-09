from typing import Dict, Any, Optional, List
import logging
from .base_agent import BaseAgent
from ....core.config.settings import get_settings

logger = logging.getLogger(__name__)

class PhaseAdvisorAgent(BaseAgent):
    """Agent that advises the user on next steps (e.g., proceeding to document drafting) based on the current phase."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        super().__init__(self.settings)
        from ...prompt_manager.manager import PromptManager
        self.prompt_manager = PromptManager()
        self.prompts = {
            "legal_basis_next_steps": self.prompt_manager.get_prompt("phase_advisor", "legal_basis_next_steps") or (
                "انتهينا من التحليل القانوني وإعداد نقاط الاعتراض استناداً إلى صحيفة الدعوى وما توفر لدينا.\n\n"
                "إذا لم يكن لديك مرفقات إضافية تريد رفعها الآن، أقترح أن ننتقل إلى مناقشة صياغة الوثائق القانونية (المذكرات/اللائحة) بناءً على النتائج الحالية.\n\n"
                "هل ترغب بالانتقال الآن إلى: مناقشة صياغة الوثائق القانونية؟"
            )
        }

    async def _process_query(self, messages: Optional[List[Dict[str, str]]] = None) -> str:
        if not messages:
            return ""
        completion = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            temperature=0.1
        )
        return completion.choices[0].message.content

    async def execute(self, query: str, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        try:
            prompt_text = self.prompts.get("legal_basis_next_steps", "")
            messages = [{"role": "system", "content": prompt_text}]
            content = await self._process_query(messages)
            return {"response": {"content": content, "metadata": {"agent_type": self.agent_type}}, "status": "success"}
        except Exception as e:
            logger.error(f"PhaseAdvisorAgent error: {e}", exc_info=True)
            return {"error": str(e), "status": "error"}

    @property
    def agent_type(self) -> str:
        return "phase_advisor" 