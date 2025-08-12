import logging
from typing import Tuple, List
import re

logger = logging.getLogger(__name__)

def parse_answer_with_embedded_citations(llm_response: str) -> Tuple[str, List[str], List[str]]:
    """
    Parses a single LLM response containing an answer with embedded citations,
    a list of used source IDs, and related questions.
    """
    answer = ""
    used_source_ids = []
    related_questions = []

    try:
        answer_match = re.search(r'<ANSWER_BLOCK>(.*?)</ANSWER_BLOCK>', llm_response, re.DOTALL)
        sources_match = re.search(r'<USED_SOURCES_BLOCK>(.*?)</USED_SOURCES_BLOCK>', llm_response, re.DOTALL)
        questions_match = re.search(r'<RELATED_QUESTIONS_BLOCK>(.*?)</RELATED_QUESTIONS_BLOCK>', llm_response, re.DOTALL)

        if answer_match:
            answer = answer_match.group(1).strip()
        else:
            logger.warning("Could not find <ANSWER_BLOCK> in LLM response. The response may be malformed.")
            # Return the whole response as the answer if the main block is missing
            return llm_response, [], []

        if sources_match:
            sources_part = sources_match.group(1).strip()
            # Find all occurrences of [doc_X]
            used_source_ids = re.findall(r'\[doc_\d+\]', sources_part)
        
        if questions_match:
            questions_part = questions_match.group(1).strip()
            related_questions = [
                q.strip().lstrip('-').strip() 
                for q in questions_part.split('\n') 
                if q.strip()
            ]

    except Exception as e:
        logger.error(f"Error parsing all-in-one LLM response: {e}. Returning raw response as answer.")
        return llm_response, [], []

    return answer, used_source_ids, related_questions

def parse_answer_and_related_questions(llm_response: str) -> Tuple[str, List[str]]:
    """
    Parses a structured LLM response that contains an answer and a list of related questions.

    The expected format is:
    ANSWER:
    [The main answer]

    RELATED_QUESTIONS:
    - [Question 1]
    - [Question 2]

    Args:
        llm_response: The raw string response from the language model.

    Returns:
        A tuple containing the extracted answer string and a list of related questions.
    """
    answer = ""
    related_questions = []

    try:
        if "RELATED_QUESTIONS:" in llm_response:
            parts = llm_response.split("RELATED_QUESTIONS:", 1)
            answer_part = parts[0]
            questions_part = parts[1]
            
            if "ANSWER:" in answer_part:
                answer = answer_part.replace("ANSWER:", "").strip()
            else:
                answer = answer_part.strip()  # Fallback if ANSWER: marker is missing

            # Clean up and split questions
            related_questions = [
                q.strip().lstrip('-').strip() 
                for q in questions_part.strip().split('\n') 
                if q.strip()
            ]
            logger.info(f"Successfully parsed {len(related_questions)} related questions.")

        else:
            # If the model doesn't follow the format, return the whole response as the answer.
            logger.warning("LLM response did not contain 'RELATED_QUESTIONS:' marker. Treating entire response as the answer.")
            answer = llm_response
    
    except Exception as e:
        logger.error(f"Error parsing LLM response: {e}. Returning raw response.")
        answer = llm_response
        related_questions = []

    return answer, related_questions

def parse_answer_with_sources(llm_response: str) -> Tuple[str, List[dict]]:
    """
    Parses a structured LLM response that contains an answer and a list of sources with quotes.

    Expected format:
    ANSWER:
    [The main answer]

    SOURCES:
    - source: [doc_1]
      quote: "[Quote from doc_1]"
    - source: [doc_2]
      quote: "[Quote from doc_2]"

    Args:
        llm_response: The raw string response from the language model.

    Returns:
        A tuple containing the answer string and a list of source dictionaries.
        Example: ("The answer.", [{"source_id": "[doc_1]", "quote": "Quote text."}])
    """
    answer = ""
    sources = []
    
    try:
        # Split the response into ANSWER and SOURCES sections
        if "SOURCES:" in llm_response:
            parts = llm_response.split("SOURCES:", 1)
            answer_part = parts[0]
            sources_part = parts[1]

            # Extract the answer
            answer = answer_part.replace("ANSWER:", "").strip()

            # Process each line in the sources part
            current_source_id = None
            for line in sources_part.strip().split('\n'):
                line = line.strip()
                if line.startswith("- source:"):
                    current_source_id = line.replace("- source:", "").strip()
                elif line.startswith("quote:") and current_source_id:
                    quote = line.replace("quote:", "").strip().strip('"')
                    sources.append({"source_id": current_source_id, "quote": quote})
                    current_source_id = None # Reset for the next source
            
            logger.info(f"Successfully parsed answer and {len(sources)} sources.")

        else:
            logger.warning("LLM response did not contain 'SOURCES:' marker. Treating entire response as answer.")
            answer = llm_response.replace("ANSWER:", "").strip()

    except Exception as e:
        logger.error(f"Error parsing response with sources: {e}. Returning raw response.")
        answer = llm_response
        sources = []

    return answer, sources 

def parse_all_in_one_response(llm_response: str) -> Tuple[str, str, List[str]]:
    """
    Parses a single LLM response containing an answer, sources, and related questions,
    each in their own block separated by XML-like tags.
    The sources block is returned as a raw markdown string.
    """
    answer = ""
    sources_markdown = ""
    related_questions = []

    try:
        # Extract content from each block using regex for robustness
        answer_match = re.search(r'<ANSWER_BLOCK>(.*?)</ANSWER_BLOCK>', llm_response, re.DOTALL)
        sources_match = re.search(r'<SOURCES_BLOCK>(.*?)</SOURCES_BLOCK>', llm_response, re.DOTALL)
        questions_match = re.search(r'<RELATED_QUESTIONS_BLOCK>(.*?)</RELATED_QUESTIONS_BLOCK>', llm_response, re.DOTALL)

        if answer_match:
            answer = answer_match.group(1).strip()
        else:
            logger.warning("Could not find <ANSWER_BLOCK> in LLM response. The response may be malformed.")
            return llm_response, "", [] # Return early if the main content is missing

        if sources_match:
            sources_markdown = sources_match.group(1).strip()
        
        if questions_match:
            questions_part = questions_match.group(1).strip()
            related_questions = [
                q.strip().lstrip('-').strip() 
                for q in questions_part.split('\n') 
                if q.strip()
            ]

    except Exception as e:
        logger.error(f"Error parsing all-in-one LLM response: {e}. Returning raw response as answer.")
        return llm_response, "", []

    return answer, sources_markdown, related_questions 

def clean_inline_source_markers(text: str) -> str:
    """Remove Azure AI Projects/Agents inline citation artifacts such as '' or '' from text.
    Also collapses excessive whitespace after removal.
    """
    try:
        if not text:
            return text
        # Remove any bracket that contains a dagger † (e.g., )
        text = re.sub(r"【[^】]*†[^】]*】", "", text)
        # Legacy patterns
        text = re.sub(r"【\s*\d+(?::\d+)?\s*†source】", "", text)
        text = re.sub(r"【[^】]*†source】", "", text)
        # Final catch-all: remove ANY 【...】 blocks
        text = re.sub(r"【[^】]*】", "", text)
        # Normalize whitespace/newlines
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    except Exception as e:
        logger.warning(f"Failed to clean inline source markers: {e}")
        return text


def normalize_pleading_phrasing(text: str) -> str:
    """Normalize Arabic pleading phrasing to avoid 'نطلب الحكم ...'.
    - Replace 'الحكم بعدم قبول الدعوى[ شكلاً]' with 'نطلب بعدم قبول الدعوى[ شكلاً]'
    - Replace 'الحكم برفض الدعوى' with 'نطلب رفض الدعوى'
    """
    try:
        if not text:
            return text
        # Keep any trailing qualifier like 'شكلاً'
        text = re.sub(r"الحكم\s+بعدم\s+قبول\s+الدعوى(\s*شكلاً)?", lambda m: "نطلب بعدم قبول الدعوى" + (m.group(1) or ""), text)
        text = re.sub(r"الحكم\s+برفض\s+الدعوى", "نطلب رفض الدعوى", text)
        return text
    except Exception as e:
        logger.warning(f"Failed to normalize pleading phrasing: {e}")
        return text 

def enforce_arabic_ordinals_in_defense_sections(text: str) -> str:
    """Ensure points under 'الدفع الشكلي' and 'الدفع الموضوعي' use Arabic ordinal labels
    like 'أولاً:', 'ثانياً:', 'ثالثاً:' instead of bullets or numeric lists.

    Strategy:
    - Detect entry into either section when a line contains a header for it.
    - While inside the section, transform top-level bullet/numbered list lines to ordinal-prefixed lines.
    - Also split inline occurrences like "أولاً: …؛ ثانياً: …" or "أولاً: … ثانياً: …" into separate lines.
    - Use Markdown bold formatting for ordinal labels: **أولاً:** (HTML may be escaped in the client).
    - Stop when another major section header is detected (الخلاصة، الطلبات، الوقائع، etc.).
    - Leave already formatted prefixes intact.
    """
    try:
        if not text:
            return text
 
        lines = text.splitlines()
 
        def is_section_header(line: str) -> bool:
            l = line.strip().replace("—", "-")
            return (
                bool(re.search(r"(?:^|\s)(الدفع\s+الشكلي)(?:\s*:|\s*$)", l)) or
                bool(re.search(r"(?:^|\s)(الدفع\s+الموضوعي)(?:\s*:|\s*$)", l))
            )
 
        def is_next_major_section(line: str) -> bool:
            l = line.strip()
            if not l:
                return False
            return any(k in l for k in [
                "الخلاصة", "الطلبات", "الوقائع", "الوقائع:", "ملخص", "الملخص", "خاتمة"
            ])
 
        arabic_ordinals = [
            "أولاً", "ثانياً", "ثالثاً", "رابعاً", "خامساً",
            "سادساً", "سابعاً", "ثامناً", "تاسعاً", "عاشراً",
        ]
 
        ord_group = "|".join([re.escape(o) for o in arabic_ordinals])
        start_prefix_re = re.compile(rf"^\s*((?:{ord_group})\s*:)\s*")
        inline_prefix_re = re.compile(rf"[؛;،]\s*((?:{ord_group})\s*:)\s*")
        mid_prefix_re = re.compile(rf"\s+((?:{ord_group})\s*:)\s*")
 
        def format_prefix(prefix: str) -> str:
            p = prefix.strip()
            # Markdown bold for better compatibility
            return f"**{p}**"
 
        def leading_spaces(s: str) -> int:
            m = re.match(r"^(\s*)", s)
            return len(m.group(1)) if m else 0
 
        def is_top_level_bullet_like(s: str) -> bool:
            if leading_spaces(s) > 1:
                return False
            return bool(re.match(r"^\s*([\-•\*\u2013\u2014]|\d+[\)\.:]|[٠-٩]+[\)\.:])\s+", s))
 
        output_lines: list[str] = []
        inside_defense_section = False
        ordinal_index = 0
 
        for line in lines:
            stripped = line.strip()
 
            if is_section_header(line):
                inside_defense_section = True
                ordinal_index = 0
                output_lines.append(stripped)
                continue
 
            if inside_defense_section:
                if is_next_major_section(line):
                    inside_defense_section = False
                    ordinal_index = 0
                    output_lines.append(line)
                    continue
 
                if not stripped:
                    output_lines.append(line)
                    continue
 
                # Case A: inline ordinals in a single sentence (e.g., "أولاً: …؛ ثانياً: …" or with space)
                if start_prefix_re.search(line) or inline_prefix_re.search(line) or mid_prefix_re.search(line):
                    # Ensure first prefix is formatted at line start
                    new_line = start_prefix_re.sub(lambda m: format_prefix(m.group(1)) + " ", line, count=1)
                    # Split subsequent prefixes into newlines, each formatted
                    new_line = inline_prefix_re.sub(lambda m: "\n" + format_prefix(m.group(1)) + " ", new_line)
                    new_line = mid_prefix_re.sub(lambda m: "\n" + format_prefix(m.group(1)) + " ", new_line)
                    split_lines = new_line.split("\n")
                    for sl in split_lines:
                        output_lines.append(sl.rstrip())
                    continue
 
                # Case B: top-level bullets => convert to ordinal with formatting
                if is_top_level_bullet_like(line):
                    prefix_txt = arabic_ordinals[ordinal_index] if ordinal_index < len(arabic_ordinals) else f"{ordinal_index+1}"
                    content = re.sub(r"^\s*([\-•\*\u2013\u2014]|\d+[\)\.:]|[٠-٩]+[\)\.:])\s+", "", line).strip()
                    output_lines.append(f"{format_prefix(prefix_txt + ':')} {content}")
                    ordinal_index += 1
                    continue
 
                # Case C: line already starts with ordinal but without bullets (ensure formatting)
                if re.match(rf"^\s*(?:{ord_group})\s*:", line):
                    output_lines.append(start_prefix_re.sub(lambda m: format_prefix(m.group(1)) + " ", line, count=1))
                    ordinal_index += 1
                    continue
 
                output_lines.append(line)
                continue
 
            output_lines.append(line)
 
        return "\n".join(output_lines)
    except Exception as e:
        logger.warning(f"Failed to enforce Arabic ordinals: {e}")
        return text 


def enforce_defense_section_preamble(text: str) -> str:
    """Ensure each defense section contains the required preamble pattern:
    - After the header line, add an 'استنادًا إلى:' block listing relevant materials if missing
    - Then add a line: 'ندفع بعدم قبول الدعوى شكلاً للأسباب التالية:' for procedural
      or 'ندفع برد الدعوى موضوعًا للأسباب التالية:' for substantive when missing

    We heuristically extract references from the section body by scanning for 'المادة (..)' phrases
    and known anchors like 'جدول الغرامات'. If none found, we keep the section as-is.
    """
    try:
        if not text:
            return text

        lines = text.splitlines()

        def is_header(line: str, kind: str) -> bool:
            l = line.strip()
            if kind == "procedural":
                return "الدفع الشكلي" in l
            return "الدفع الموضوعي" in l

        def is_section_break(line: str) -> bool:
            l = line.strip()
            if not l:
                return False
            return any(k in l for k in ["الخلاصة", "الطلبات"]) or ("الدفع" in l and ("الشكلي" in l or "الموضوعي" in l))

        def collect_refs(section_lines: list[str]) -> list[str]:
            refs: list[str] = []
            import re as _re
            joined = "\n".join(section_lines)
            # Find 'المادة (xx) من ...' sequences
            for m in _re.finditer(r"المادة\s*\([^)]+\)\s*من\s*[^\n،\.]+", joined):
                ref = m.group(0).strip()
                if not ref.endswith("،"):
                    ref += "،"
                refs.append(ref)
                if len(refs) >= 4:
                    break
            # Add known anchors if present
            if "جدول الغرامات" in joined and len(refs) < 5:
                refs.append("جدول الغرامات والجزاءات البلدية،")
            # De-duplicate preserving order
            seen = set()
            unique = []
            for r in refs:
                if r not in seen:
                    unique.append(r)
                    seen.add(r)
            return unique

        def insert_preamble(start_idx: int, end_idx: int, kind: str) -> tuple[int, int]:
            # Build updated block with preamble if missing
            block = lines[start_idx:end_idx]
            block_str = "\n".join(block)
            need_preamble = ("استنادًا" not in block_str and "استنادا" not in block_str)
            need_decision_line = True
            if kind == "procedural":
                decision_line = "ندفع بعدم قبول الدعوى شكلاً للأسباب التالية:"
                if "عدم قبول الدعوى" in block_str and "الأسباب التالية" in block_str:
                    need_decision_line = False
            else:
                decision_line = "ندفع برد الدعوى موضوعًا للأسباب التالية:"
                if ("رد الدعوى" in block_str or "رفض الدعوى" in block_str) and "الأسباب التالية" in block_str:
                    need_decision_line = False

            inserted = []
            if need_preamble:
                refs = collect_refs(block)
                if refs:
                    inserted.append("استنادًا إلى:")
                    inserted.extend(refs)
            if need_decision_line:
                inserted.append(decision_line)

            if inserted:
                # Insert right after header (which is at start_idx)
                # Preserve any blank line following header
                header_line = lines[start_idx]
                i = start_idx + 1
                while i < end_idx and not lines[i].strip():
                    i += 1
                new_block = [header_line] + ([""] if (i == start_idx + 1 and lines[start_idx + 1].strip() == "") else []) + inserted + [""] + lines[i:end_idx]
                lines[start_idx:end_idx] = new_block
                # New end index after insertion
                end_idx = start_idx + len(new_block)
            return start_idx, end_idx

        i = 0
        n = len(lines)
        while i < n:
            if is_header(lines[i], "procedural"):
                j = i + 1
                while j < n and not is_section_break(lines[j]):
                    j += 1
                i, j = insert_preamble(i, j, "procedural")
                n = len(lines)
                i = j
                continue
            if is_header(lines[i], "substantive"):
                j = i + 1
                while j < n and not is_section_break(lines[j]):
                    j += 1
                i, j = insert_preamble(i, j, "substantive")
                n = len(lines)
                i = j
                continue
            i += 1

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Failed to enforce defense preamble: {e}")
        return text 