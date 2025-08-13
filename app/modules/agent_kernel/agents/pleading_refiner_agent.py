from typing import Optional, List, Dict
import logging
from .base_agent import BaseAgent
from ....core.config.settings import get_settings

logger = logging.getLogger(__name__)

class PleadingRefinerAgent(BaseAgent):
    """Refines the pleading body (after header) to a clean, serious legal markdown structure.
    - Keeps the header unchanged
    - Ensures two sections only: الدفع الشكلي، الدفع الموضوعي
    - Adds/keeps reference preambles and 'للأسباب التالية:' lines
    - Converts reasons to plain lines (no numbering) and bolds important phrases/statutes
    - Removes code fences and technical artifacts
    """

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        super().__init__(self.settings)
        from ...prompt_manager.manager import PromptManager
        self.prompt_manager = PromptManager()
        self.prompt = self.prompt_manager.get_prompt("legal_basis", "pleading_refiner") or (
            "أنت محامٍ محرّر لوثائق قضائية. لديك نص لائحة رد يتضمن ترويسة (Header) في الأعلى ثم المحتوى.\n"
            "المطلوب: أعِد صياغة محتوى اللائحة فقط (بعد الترويسة) بنَفَس مهني رصين وبصيغة ماركداون نظيفة، مع الحفاظ على الترويسة كما هي.\n"
            "التزم بما يلي:\n"
            "1) الأقسام حصراً: # ثانياً: الدفع الشكلي ثم # ثالثاً: الدفع الموضوعي.\n"
            "2) بداية كل قسم بسطر 'استنادًا إلى:' تليه المواد/اللوائح ذات الصلة، كل مرجع في سطر مستقل.\n"
            "3) بعد المواد مباشرةً:\n   - في الدفع الشكلي: 'ندفع بعدم قبول الدعوى شكلاً للأسباب التالية:'\n   - في الدفع الموضوعي: 'ندفع برد الدعوى موضوعًا للأسباب التالية:'\n"
            "4) الأسباب تُكتب كجمل كاملة متسلسلة بدون ترقيم (كل سبب في سطر مستقل).\n"
            "5) استخدم الغلاظة (Bold) لتمييز العبارات الجوهرية والإشارات النظامية (مثل **المادة 187**).\n"
            "6) لا تُدرج قسمي 'الخلاصة' أو 'الطلبات'.\n"
            "7) ممنوع أقواس المصادر التقنية أو كتل الكود، ولا تُضف مصادر جديدة.\n"
            "نص اللائحة (خط فاصل بعد الترويسة):\n"
            "-----\n"
            "{{PLEADING_TEXT}}"
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

    async def refine(self, pleading_text: str, example: Optional[str] = None, facts_text: Optional[str] = None) -> str:
        prompt = self.prompt.replace("{{PLEADING_TEXT}}", pleading_text or "")
        # If facts are provided, instruct to prepend a '# أولاً: الوقائع' (2–4 lines) before the defenses
        if facts_text:
            prompt += (
                "\n\nإذا توفر نص وقائع أدناه، فابدأ قبل أقسام الدفع بقسم بعنوان '# أولاً: الوقائع' يتكون من سطرين إلى أربعة أسطر،"
                " يلخص الوقائع بوضوح دون أقواس تقنية أو تعداد: \n"
                "[نص الوقائع]\n" + (facts_text[:4000])
            )
        if example:
            prompt = (
                prompt
                + "\n\nمثال إرشادي للبنية (التزم بالهيكل ولا تنقل النص حرفياً):\n"
                + example.strip()
            )
        return await self._process_query([{"role": "system", "content": prompt}])

    @property
    def agent_type(self) -> str:
        return "pleading_refiner" 