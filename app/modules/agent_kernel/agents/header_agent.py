from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent

class HeaderAgent(BaseAgent):
    """A minimal agent that formats the legal pleading header from provided claim metadata.
    It does not call the LLM for generation; it only assembles fields deterministically
    to avoid hallucinations.
    """

    @property
    def agent_type(self) -> str:
        return "header"

    async def _process_query(self, messages: Optional[List[Dict[str, str]]] = None) -> str:
        # Expect last user message to be a JSON-like payload with fields
        query = messages[-1]["content"] if messages else ""
        data: Dict[str, Any] = {}
        try:
            import json
            data = json.loads(query) if query.strip().startswith("{") else {}
        except Exception:
            data = {}

        # Optionally fetch claim by conversation_id if given
        if data.get("conversation_id") and not data.get("claim_text"):
            try:
                from app.core.database import db_manager
                db = db_manager.db
                soc = await db.statement_of_claim.find_one({"conversation_id": data["conversation_id"]})
                if soc:
                    data["claim_text"] = soc.get("raw_text", "")
                    data.setdefault("case_number", soc.get("case_number"))
                    data.setdefault("plaintiff_name", soc.get("plaintiff_name"))
                    data.setdefault("court", soc.get("court"))
            except Exception:
                pass

        court = (data.get("court") or "المحكمة الإدارية").strip()
        case_number = (data.get("case_number") or "—").strip()
        year_h = (data.get("year_h") or "1447").strip()
        plaintiff_name = (data.get("plaintiff_name") or "—").strip()
        defendant_name = (data.get("defendant_name") or "وزارة البلديات والإسكان").strip()

        header = (
            "رجاءً التزم بهذا القالب النهائي حرفيًا عند توليد المذكرة:\n\n"
            f"فضيلة رئيس وأعضاء الدائرة ........ بالمحكمة الإدارية {court}           سلمهم الله\n"
            "السلام عليكم ورحمة الله وبركاته\n"
            f"مذكرة جوابية مقدمة من {defendant_name}\n"
            f"في الدعوى رقم ({case_number}) لعام {year_h}هـ\n"
            f"المدعي: {plaintiff_name}\n"
            f"المدعى عليها: {defendant_name}\n"
        )
        return header 