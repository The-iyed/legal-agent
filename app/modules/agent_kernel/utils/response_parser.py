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
    - Stop when another major section header is detected (الخلاصة، الطلبات، الوقائع، etc.).
    - Leave lines already starting with an Arabic ordinal unchanged.
    """
    try:
        if not text:
            return text

        lines = text.splitlines()

        def is_section_header(line: str) -> bool:
            l = line.strip().replace("—", "-")
            # Match possible forms like: "ثانياً: الدفع الشكلي", "الدفع الشكلي", etc.
            return (
                bool(re.search(r"(?:^|\s)(الدفع\s+الشكلي)(?:\s*:|\s*$)", l)) or
                bool(re.search(r"(?:^|\s)(الدفع\s+الموضوعي)(?:\s*:|\s*$)", l))
            )

        def is_next_major_section(line: str) -> bool:
            l = line.strip()
            if not l:
                return False
            # Do not treat other 'الدفع' lines as major section boundaries; headers are handled separately
            return any(k in l for k in [
                "الخلاصة", "الطلبات", "الوقائع", "الوقائع:", "ملخص", "الملخص", "خاتمة"
            ])

        arabic_ordinals = [
            "أولاً", "ثانياً", "ثالثاً", "رابعاً", "خامساً",
            "سادساً", "سابعاً", "ثامناً", "تاسعاً", "عاشراً",
        ]

        def line_has_arabic_ordinal_prefix(s: str) -> bool:
            return bool(re.match(r"^\s*(أولاً|ثانياً|ثالثاً|رابعاً|خامساً|سادساً|سابعاً|ثامناً|تاسعاً|عاشراً)\s*:\s*", s))

        def leading_spaces(s: str) -> int:
            m = re.match(r"^(\s*)", s)
            return len(m.group(1)) if m else 0

        def is_top_level_bullet_like(s: str) -> bool:
            # Accept common dash bullets and numeric bullets only if not indented (<= 1 space)
            if leading_spaces(s) > 1:
                return False
            return bool(re.match(r"^\s*([\-•\*\u2013\u2014]|\d+[\)\.:]|[٠-٩]+[\)\.:])\s+", s))

        inside_defense_section = False
        ordinal_index = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Always detect section headers
            if is_section_header(line):
                inside_defense_section = True
                ordinal_index = 0
                lines[i] = stripped  # normalize header whitespace only
                continue

            if inside_defense_section:
                # If we hit another major (non-defense) section, stop enumerating
                if is_next_major_section(line):
                    inside_defense_section = False
                    ordinal_index = 0
                    continue

                if not stripped:
                    continue

                # Skip if already ordinal-prefixed
                if line_has_arabic_ordinal_prefix(line):
                    continue

                # Transform only top-level bullet/numbered lines to ordinal
                if is_top_level_bullet_like(line):
                    prefix = arabic_ordinals[ordinal_index] if ordinal_index < len(arabic_ordinals) else f"{ordinal_index+1}"
                    # Remove common bullet markers before applying
                    content = re.sub(r"^\s*([\-•\*\u2013\u2014]|\d+[\)\.:]|[٠-٩]+[\)\.:])\s+", "", line).strip()
                    lines[i] = f"{prefix}: {content}"
                    ordinal_index += 1
                    continue

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Failed to enforce Arabic ordinals: {e}")
        return text 