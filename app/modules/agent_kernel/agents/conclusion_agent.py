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
            "أنت محامٍ محترف. لديك عناصر الاعتماد الآتية: [تحليل نهائي]، [نص صحيفة الدعوى]، [مقتطفات المرفقات]، و[نص جسم اللائحة المنقّح].\n"
            "المطلوب: صِغ قسمين فقط وبعربية قانونية حاسمة (بدون تردد أو ألفاظ احتمالية مثل 'قد/ربما/يُتوقع') وبدون أقواس تقنية أو كتل كود: \n\n"
            "الخلاصة: اكتب 2–4 أسطر حاسمة تبدأ بصياغات مثل 'الثابت من الأوراق/الوقائع' وتنتهي بعبارة تقريرية لا تحتمل التردد.\n\n"
            "الطلبات: نقاط موجزة بسطر مستقل لكل طلب. اطلب برفض الدعوى موضوعاً وإلزام المدعي بالمصاريف وأتعاب المحاماة، ويمكن إضافة 'تأييد محضر الضبط والإجراءات' إن كانت ثابتة. \n"
            "- لا تُدرج 'عدم قبول الدعوى شكلاً' إلا إذا تبيّن من [نص جسم اللائحة] أن أسباب عدم القبول الشكلي قائمة ومذكورة صراحةً؛ خلاف ذلك لا تذكره.\n"
            "- يمنع استعمال صيغ معلّقة من نوع '(إن توافرت أسبابه)'.\n\n"
            "[التحليل النهائي]\n{{FINAL_ANALYSIS}}\n\n[صحيفة الدعوى]\n{{CLAIM_TEXT}}\n\n[المرفقات]\n{{ATTACHMENTS_TEXT}}\n\n[نص جسم اللائحة المنقّح]\n{{PLEADING_BODY}}"
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

    async def generate(self, final_analysis: str, claim_text: str, attachments_text: str, body_text: str = "") -> str:
        prompt = (
            self.prompt
            .replace("{{FINAL_ANALYSIS}}", final_analysis or "")
            .replace("{{CLAIM_TEXT}}", claim_text or "")
            .replace("{{ATTACHMENTS_TEXT}}", attachments_text or "")
            .replace("{{PLEADING_BODY}}", body_text or "")
        )
        return await self._process_query([{"role": "system", "content": prompt}])

    @property
    def agent_type(self) -> str:
        return "conclusion" 