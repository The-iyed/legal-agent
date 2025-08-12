from typing import Dict, Any, Optional, List
import logging
from .base_agent import BaseAgent
from ....core.config.settings import get_settings

logger = logging.getLogger(__name__)

class ConclusionAgent(BaseAgent):
    """Generates the 'الخلاصة' and 'الطلبات' sections based on analysis, claim, and attachments."""

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        super().__init__(self.settings)
        from ...prompt_manager.manager import PromptManager
        self.prompt_manager = PromptManager()
        self.prompt = self.prompt_manager.get_prompt("legal_basis", "conclusion") or (
            "أنت محامٍ محترف. بالنظر إلى: [تحليل نهائي مختصر]، [نص صحيفة الدعوى]، [مقتطفات المرفقات]، أعد صياغة قسمين فقط وبالعربية القانونية دون مقدمات: \n\n"
            "الخلاصة: سطران إلى أربعة أسطر تلخص موقف الجهة والنتيجة المتوقعة دون ذكر مصادر أو أقواس خاصة.\n\n"
            "الطلبات: نقاط موجزة بسطر مستقل لكل طلب. استخدم الشكل: - عدم قبول الدعوى شكلاً (إن توافرت أسبابه). - رفض الدعوى موضوعاً. - تحميل المدعي المصاريف وأتعاب المحاماة. عدّل الصياغة وفق المعطيات وتجنّب الأقواس المربعة/المرقمة."
        )

    async def _process_query(self, messages: Optional[List[Dict[str, str]]] = None) -> str:
        if not messages:
            return ""
        completion = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            temperature=0.1
        )
        return completion.choices[0].message.content

    async def generate(self, final_analysis: str, claim_text: str, attachments_text: str) -> str:
        prompt = (
            self.prompt
            .replace("{{FINAL_ANALYSIS}}", final_analysis or "")
            .replace("{{CLAIM_TEXT}}", claim_text or "")
            .replace("{{ATTACHMENTS_TEXT}}", attachments_text or "")
        )
        return await self._process_query([{"role": "system", "content": prompt}])

    @property
    def agent_type(self) -> str:
        return "conclusion" 