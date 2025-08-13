from typing import Dict, Any, Optional, List
import asyncio
import logging
from .base_agent import BaseAgent
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType, QueryCaptionType, QueryAnswerType
from ....core.config.settings import get_settings
import re

logger = logging.getLogger(__name__)


class LegalBasisAgent(BaseAgent):
    """Agent to analyze legal basis of a claim + attachments and suggest defense points."""

    def __init__(self, settings=None):
        # Ensure we have a settings object and initialize BaseAgent properly
        self.settings = settings or get_settings()
        super().__init__(self.settings)
        # Azure AI Search setup
        self.search_endpoint = self.settings.AZURE_AI_SEARCH_ENDPOINT
        self.search_api_key = self.settings.AZURE_AI_SEARCH_API_KEY
        # Use index name from settings (fallback to 'sheet-documents')
        self.search_index_name = self.settings.AZURE_AI_SEARCH_STUDY_INDEX_NAME or "sheet-documents"
        self.search_client: Optional[SearchClient] = None
        if self.search_endpoint and self.search_api_key:
            self.search_client = SearchClient(
                endpoint=self.search_endpoint,
                index_name=self.search_index_name,
                credential=AzureKeyCredential(self.search_api_key)
            )

        # Load prompts for stages
        from ...prompt_manager.manager import PromptManager
        self.prompt_manager = PromptManager()
        self.prompts = {
            "extract_issues": self.prompt_manager.get_prompt("legal_basis", "extract_issues") or "",
            "search_plan": self.prompt_manager.get_prompt("legal_basis", "search_plan") or "",
            "analysis": self.prompt_manager.get_prompt("legal_basis", "analysis") or "",
            "defense": self.prompt_manager.get_prompt("legal_basis", "defense") or "",
            "update": self.prompt_manager.get_prompt("legal_basis", "update") or (
                "أنت محامٍ مختص. لديك تحليل سابق للأساس القانوني (نص سابق)، ونص الدعوى، ومرفقات جديدة.\n"
                "المطلوب: أعد فقط تحديثاً موجزاً ومنظماً يبيّن:\n"
                "- النقاط التي تغيّرت أو تقوَّت بسبب المرفقات الجديدة.\n"
                "- أي مواد/مبادئ قانونية إضافية يجب أخذها في الاعتبار.\n"
                "- نقاط دفاع جديدة أو مُحسّنة للجهة البلدية.\n"
                "اكتب بالعربية القانونية وبشكل مختصر، دون تكرار التحليل السابق، وميّز التحديث بعنوان واضح." 
            ),
            "pleading_strict": (
                "أنت محامٍ محترف. صِغ جسم لائحة الرد منظمًا على قسمين: الدفع الشكلي، الدفع الموضوعي.\n"
                "اعتمد بشكل أساسي على التحليل النهائي ونص الدعوى؛ لا تستند إلى نص المرفقات الخام مباشرة.\n"
                "- أدرِج جملة مرجعية نظامية ديناميكية قبل كل قسم تنتهي بعبارة ‘للأسباب التالية:’.\n"
                "- اكتب الأسباب في سطور منفصلة تبدأ بـ: **أولاً:**، **ثانياً:**، **ثالثاً:** …\n"
                "- لا تستخدم أقواس مراجع مربعة/أرقام، ولا تذكر مصادر تقنية.\n"
                "[التحليل النهائي]\n{{FINAL_ANALYSIS}}\n\n[صحيفة الدعوى]\n{{CLAIM_TEXT}}"
            ),
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

    async def generate_pleading(self, claim_text: str, attachments_text: str, final_analysis: str, case_number: str = "" , plaintiff_name: str = "") -> str:
        """Generate a formal legal pleading memo based on claim, attachments, and final analysis."""
        prompt = self.prompt_manager.get_prompt("legal_basis", "pleading") or self.prompts.get("analysis", "")
        # Extract defendant name from claim_text when possible (simple heuristics)
        defendant_name = "وزارة البلديات والإسكان/الأمانة"
        try:
            import re as _re
            # Common Arabic label patterns
            m = _re.search(r"(?:المدعى\s+عليه|المدعى\s+عليها|الجهة\s+المدعى\s+عليها)\s*[:：]?\s*([^\n\r]+)", claim_text or "", flags=_re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                # Clean trailing punctuation
                cand = _re.sub(r"[\s\-–—:,]+$", "", cand)
                if 2 <= len(cand) <= 120:
                    defendant_name = cand
        except Exception:
            pass
        prompt = (
            (self.prompts.get("pleading_strict") or prompt)
            .replace("{{CLAIM_TEXT}}", claim_text or "")
            .replace("{{ATTACHMENTS_TEXT}}", attachments_text or "")
            .replace("{{FINAL_ANALYSIS}}", final_analysis or "")
            .replace("{{CASE_NUMBER}}", case_number or "—")
            .replace("{{PLAINTIFF_NAME}}", plaintiff_name or "—")
            .replace("{{DEFENDANT_NAME}}", defendant_name)
        )
        return await self._process_query([{"role": "system", "content": prompt}])

    def _sanitize_output(self, text: str) -> str:
        if not text:
            return ""
        # Remove fenced code blocks like ```markdown ... ```
        text = re.sub(r"```[a-zA-Z]*\s*([\s\S]*?)```", r"\1", text, flags=re.MULTILINE)
        # Strip markdown headers (#####, ####, ###, ##, #)
        text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
        # Remove horizontal rules
        text = re.sub(r"^\s*---\s*$", "", text, flags=re.MULTILINE)
        # Collapse excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    async def _stage_extract_issues(self, claim_text: str, attachments_text: str) -> str:
        prompt = self.prompts["extract_issues"].replace("{{CLAIM_TEXT}}", claim_text).replace("{{ATTACHMENTS_TEXT}}", attachments_text)
        messages = [{"role": "system", "content": prompt}]
        return await self._process_query(messages)

    async def _stage_search_plan(self, issues: str) -> List[str]:
        prompt = self.prompts["search_plan"].replace("{{ISSUES}}", issues)
        messages = [{"role": "system", "content": prompt}]
        plan_text = await self._process_query(messages)
        # Split into queries, one per line bullet
        queries = [q.strip("- • \t ") for q in plan_text.splitlines() if q.strip()]
        return queries[:7]

    async def _search_laws(self, queries: List[str], top: int = 5) -> List[Dict[str, Any]]:
        if not self.search_client:
            logger.warning("LegalBasisAgent: Search client not configured, skipping search")
            return []
        select_fields = [
            "attachment_id", "document_name", "content", "legislation_title", "legislation_number", "legislation_type",
            "legislation_date", "legislation_subject", "issuing_authority", "legal_status", "page_number"
        ]
        results: List[Dict[str, Any]] = []
        loop = asyncio.get_running_loop()

        def do_semantic_search(search_query: str):
            return self.search_client.search(
                search_query,
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="my-semantic-config",
                query_caption=QueryCaptionType.EXTRACTIVE,
                query_answer=QueryAnswerType.EXTRACTIVE,
                select=select_fields,
                top=top,
            )
        for q in queries:
            try:
                search_results = await loop.run_in_executor(None, do_semantic_search, q)
                results.extend([dict(r) for r in search_results])
            except Exception as e:
                logger.warning(f"LegalBasisAgent: search failed for '{q}': {e}")
        return results[:20]

    async def _stage_analysis(self, claim_text: str, attachments_text: str, issues: str, laws: List[Dict[str, Any]], attachment_filenames: Optional[List[str]] = None, irrelevant_attachments: Optional[List[str]] = None, mandatory_highlights: Optional[List[str]] = None, adverse_files: Optional[List[str]] = None) -> str:
        laws_snippets = []
        for i, r in enumerate(laws[:12], 1):
            title = r.get("legislation_title") or r.get("document_name") or "(بدون عنوان)"
            content = r.get("content", "")
            laws_snippets.append(f"[{i}] {title}:\n{content}")
        laws_block = "\n\n".join(laws_snippets)
        filenames_block = "\n".join(attachment_filenames or [])
        irrelevant_block = "\n".join(irrelevant_attachments or [])
        highlights_block = "\n".join(mandatory_highlights or [])
        prompt = (
            self.prompts["analysis"]
            .replace("{{CLAIM_TEXT}}", claim_text)
            .replace("{{ATTACHMENTS_TEXT}}", attachments_text)
            .replace("{{ISSUES}}", issues)
            .replace("{{LAWS}}", laws_block)
            .replace("{{ATTACHMENT_FILENAMES}}", filenames_block)
            .replace("{{IRRELEVANT_ATTACHMENTS}}", irrelevant_block)
            .replace("{{MANDATORY_HIGHLIGHTS}}", highlights_block)
            .replace("{{ADVERSE_FILES}}", "\n".join(adverse_files or []))
        )
        return await self._process_query([{"role": "system", "content": prompt}])

    async def _stage_defense(self, analysis: str, laws: List[Dict[str, Any]]) -> str:
        citations = []
        for i, r in enumerate(laws[:8], 1):
            title = r.get("legislation_title") or r.get("document_name") or "(بدون عنوان)"
            num = r.get("legislation_number", "")
            citations.append(f"[{i}] {title} {num}")
        refs = "\n".join(citations)
        prompt = self.prompts["defense"].replace("{{ANALYSIS}}", analysis).replace("{{LAW_REFS}}", refs)
        return await self._process_query([{"role": "system", "content": prompt}])

    async def update_with_new_attachments(self, previous_analysis: str, claim_text: str, new_attachments_text: str) -> str:
        """Produce a concise addendum to the prior legal-basis analysis based on new attachments."""
        if not (previous_analysis and new_attachments_text):
            return "لا يوجد تحديث: يجب توفر تحليل سابق ونص مرفقات جديدة."
        system_prompt = self.prompts["update"].replace("{{PREVIOUS_ANALYSIS}}", previous_analysis).replace("{{CLAIM_TEXT}}", claim_text).replace("{{NEW_ATTACHMENTS_TEXT}}", new_attachments_text)
        return await self._process_query([{"role": "system", "content": system_prompt}])

    async def execute_without_search(self, query: str, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Run legal-basis analysis without using Azure Search (no external retrieval)."""
        try:
            claim_text = ""
            attachments_text = ""
            attachment_filenames: List[str] = []
            if isinstance(context, list):
                for item in context:
                    if item.get("_key") == "claim_text":
                        claim_text = item.get("_value", "")
                    if item.get("_key") == "attachments_text":
                        attachments_text = item.get("_value", "")
                    if item.get("_key") == "attachment_filenames":
                        val = item.get("_value")
                        if isinstance(val, list):
                            attachment_filenames = [str(v) for v in val if v]
            # Extract issues from provided texts only
            issues = await self._stage_extract_issues(claim_text, attachments_text)
            # Skip planning and search; use empty laws list
            laws: List[Dict[str, Any]] = []
            # Core analysis and defense without citations
            analysis = await self._stage_analysis(claim_text, attachments_text, issues, laws, attachment_filenames)
            defense = await self._stage_defense(analysis, laws)
            response = (
                "🎯 الأساس القانوني للدعوى   \n\n" + analysis.strip() + "\n\n"
                "🛡️ نقاط الدفاع المقترحة للبلدية\n\n" + defense.strip()
            )
            return {"response": {"content": response, "metadata": {"agent_type": self.agent_type}}, "status": "success"}
        except Exception as e:
            logger.error(f"Error in LegalBasisAgent.execute_without_search: {e}", exc_info=True)
            return {"error": str(e), "status": "error"}

    async def execute(self, query: str, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        try:
            claim_text = ""
            attachments_text = ""
            attachment_filenames: List[str] = []
            # Expect claim_text and attachments_text via context with special keys if provided
            if isinstance(context, list):
                for item in context:
                    if item.get("_key") == "claim_text":
                        claim_text = item.get("_value", "")
                    if item.get("_key") == "attachments_text":
                        attachments_text = item.get("_value", "")
                    if item.get("_key") == "attachment_filenames":
                        val = item.get("_value")
                        if isinstance(val, list):
                            attachment_filenames = [str(v) for v in val if v]
            issues = await self._stage_extract_issues(claim_text, attachments_text)
            queries = await self._stage_search_plan(issues)
            laws = await self._search_laws(queries)
            # Extract optional mandatory highlights
            highlights = []
            try:
                for item in (context or []):
                    if item.get("_key") == "mandatory_highlights":
                        val = item.get("_value")
                        if isinstance(val, list):
                            highlights = [str(v) for v in val if v]
            except Exception:
                highlights = []
            # Heuristic adversarial files: names likely from plaintiff or that could be adverse
            adverse = []
            try:
                for name in attachment_filenames:
                    if any(k in name for k in ["المدعي", "مذكرة", "اعتراض", "دعوى", "مطالبة"]):
                        adverse.append(name)
            except Exception:
                adverse = []
            analysis = await self._stage_analysis(claim_text, attachments_text, issues, laws, attachment_filenames, None, highlights, adverse)
            defense = await self._stage_defense(analysis, laws)
            # Sanitize to avoid duplicated markdown blocks or fenced code
            analysis = self._sanitize_output(analysis)
            defense = self._sanitize_output(defense)
            response = (
                "🎯 الأساس القانوني للدعوى   \n\n" + analysis.strip() + "\n\n"
                "🛡️ نقاط الدفاع المقترحة للبلدية\n\n" + defense.strip()
            )
            return {"response": {"content": response, "metadata": {"agent_type": self.agent_type}}, "status": "success"}
        except Exception as e:
            logger.error(f"Error in LegalBasisAgent execution: {e}", exc_info=True)
            return {"error": str(e), "status": "error"}

    @property
    def agent_type(self) -> str:
        return "legal_basis" 