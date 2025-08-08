import logging
from typing import List, Dict, Any, Optional

from app.core.config.settings import get_settings
from app.core.database import get_database
from openai import AzureOpenAI

logger = logging.getLogger(__name__)


class AttachmentsAnalysisService:
    """Generates a human, lawyer-style overview of attachments grounded in the claim text and attachments content."""

    def __init__(self):
        self.settings = get_settings()
        self.db = get_database()
        self.client: Optional[AzureOpenAI] = None
        try:
            if self.settings.AZURE_OPENAI_API_KEY and self.settings.AZURE_OPENAI_ENDPOINT and self.settings.AZURE_OPENAI_DEPLOYMENT_NAME:
                self.client = AzureOpenAI(
                    api_key=self.settings.AZURE_OPENAI_API_KEY,
                    api_version=self.settings.AZURE_OPENAI_API_VERSION or "2024-02-15-preview",
                    azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
                )
                self.deployment_name = self.settings.AZURE_OPENAI_DEPLOYMENT_NAME
                logger.info("AttachmentsAnalysisService: Azure OpenAI client initialized")
        except Exception as e:
            logger.warning(f"AttachmentsAnalysisService: OpenAI init failed: {e}")
            self.client = None

    async def _fetch_claim_text(self, conversation_id: str) -> str:
        doc = await self.db.statement_of_claim.find_one({"conversation_id": conversation_id})
        if not doc:
            return ""
        return (doc.get("raw_text") or "").strip()

    async def _fetch_attachments_texts(self, conversation_id: str) -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []
        cursor = self.db.attachments.find({"conversation_id": conversation_id}).sort("created_at", 1)
        async for att in cursor:
            name = att.get("filename", "مرفق")
            text = ((att.get("extracted_content", {}) or {}).get("raw_text", "") or "").strip()
            if text:
                results.append({"filename": name, "text": text})
        return results

    async def generate_attachments_overview(self, conversation_id: str) -> str:
        """
        Build a human, concise bullet list describing each attachment and its purpose in the case.
        Uses full claim text (no truncation) and full attachments content.
        """
        claim_text = await self._fetch_claim_text(conversation_id)
        attachments = await self._fetch_attachments_texts(conversation_id)

        if not attachments:
            return "لا توجد مرفقات محفوظة في هذه المحادثة."  # Arabic: No attachments stored

        # If OpenAI is not available, return simple bullets based on first lines
        if not self.client:
            bullets = []
            for att in attachments:
                first_line = att["text"].splitlines()[0].strip() if att["text"] else "(لا يوجد نص)"
                bullets.append(f"• {att['filename']}: {first_line}")
            return "\n".join(bullets)

        # Prepare grounded prompt
        docs_parts = []
        for i, att in enumerate(attachments, 1):
            docs_parts.append(f"[{i}] {att['filename']}\n{att['text']}")
        attachments_block = "\n\n".join(docs_parts)

        system_prompt = (
            "أنت محامٍ مختص. قدّم قائمة نقاط موجزة، بند واحد لكل مرفق، تصف ما يتحدث عنه المرفق وما الغاية منه في سياق صحيفة الدعوى.\n"
            "التزم بما يلي: \n"
            "- اعتمد حصراً على نص صحيفة الدعوى ونصوص المرفقات الواردة أدناه.\n"
            "- لا تنسخ نصوصاً حرفية ولا تُدرج روابط أو بيانات تقنية.\n"
            "- لا تستخدم معرفة خارجية.\n"
            "- الصيغة لكل بند: • <اسم الملف>: <وصف قصير> — الأهمية في الدعوى: <سبب الأهمية>."
        )
        user_prompt = (
            f"نص صحيفة الدعوى:\n{claim_text}\n\n"
            f"نصوص المرفقات:\n{attachments_block}"
        )

        try:
            completion = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=1800,
            )
            content = (completion.choices[0].message.content or "").strip()
            return content or "لا يوجد تلخيص متاح حالياً للمرفقات."
        except Exception as e:
            logger.error(f"AttachmentsAnalysisService: LLM generation failed: {e}")
            # Fallback simple bullets
            bullets = []
            for att in attachments:
                first_line = att["text"].splitlines()[0].strip() if att["text"] else "(لا يوجد نص)"
                bullets.append(f"• {att['filename']}: {first_line}")
            return "\n".join(bullets) 