"""
Text Processor for Claim Extraction

This module handles the processing and structuring of raw text extracted
from legal documents to identify and extract claim-related information.
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class TextProcessor:
    """Processes raw text to extract structured claim information."""
    
    def __init__(self):
        # Define patterns for different types of information
        self.patterns = self._initialize_patterns()
        logger.info("TextProcessor initialized")
    
    def _initialize_patterns(self) -> Dict[str, List[str]]:
        """Initialize regex patterns for different field types."""
        return {
            "case_number": [
                r"رقم\s*قيد\s*الدعوى\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                r"رقم\s*الطلب\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                r"رقم\s*القضية\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                r"رقم\s*الدعوى\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                r"case\s*number\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                r"رقم\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)"
            ],
            "claim_number": [
                r"رقم\s*الطلب\s*[:\-]?\s*([^\n\r]+)",
                r"رقم\s*المطالبة\s*[:\-]?\s*([^\n\r]+)",
                r"claim\s*number\s*[:\-]?\s*([^\n\r]+)"
            ],
            "filing_date": [
                r"تاريخ\s*رفع\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                r"تاريخ\s*التقديم\s*[:\-]?\s*([^\n\r]+)",
                r"التاريخ\s*[:\-]?\s*([^\n\r]+)",
                r"filing\s*date\s*[:\-]?\s*([^\n\r]+)",
                r"(\d{4}/\d{2}/\d{2})",
                r"(\d{4}-\d{2}-\d{2})"
            ],
            "plaintiff_name": [
                r"(عبير\s*احمد\s*سعيد\s*العمودي)",
                r"الاسم\s*[:\-]?\s*([^\n\r]+)",
                r"اسم\s*المدعي\s*[:\-]?\s*([^\n\r]+)",
                r"المدعي\s*[:\-]?\s*([^\n\r]+)",
                r"مقدم\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                r"مقدم\s*الطلب\s*[:\-]?\s*([^\n\r]+)",
                r"plaintiff\s*[:\-]?\s*([^\n\r]+)"
            ],
            "plaintiff_id": [
                r"رقم\s*هوية\s*المدعي\s*[:\-]?\s*([^\n\r]+)",
                r"هوية\s*المدعي\s*[:\-]?\s*([^\n\r]+)",
                r"([٠١٢٣٤٥٦٧٨٩\d]{10})"
            ],
            "plaintiff_mobile": [
                r"رقم\s*الجوال\s*[:\-]?\s*([^\n\r]+)",
                r"الجوال\s*[:\-]?\s*([^\n\r]+)",
                r"الهاتف\s*[:\-]?\s*([^\n\r]+)",
                r"([٠١٢٣٤٥٦٧٨٩\d]{10})"
            ],
            "plaintiff_email": [
                r"البريد\s*الإلكتروني\s*[:\-]?\s*([^\n\r]+)",
                r"الإيميل\s*[:\-]?\s*([^\n\r]+)",
                r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
            ],
            "plaintiff_address": [
                r"عنوان\s*المدعي\s*[:\-]?\s*([^\n\r]+)",
                r"العنوان\s*[:\-]?\s*([^\n\r]+)",
                r"address\s*[:\-]?\s*([^\n\r]+)"
            ],
            "defendant_name": [
                r"(امانه\s*منطقه\s*الرياض)",
                r"الاسم\s*[:\-]?\s*([^\n\r]+)",
                r"اسم\s*المدعى\s*عليه\s*[:\-]?\s*([^\n\r]+)",
                r"المدعى\s*عليه\s*[:\-]?\s*([^\n\r]+)",
                r"الخصم\s*[:\-]?\s*([^\n\r]+)",
                r"defendant\s*[:\-]?\s*([^\n\r]+)"
            ],
            "defendant_type": [
                r"نوع\s*المدعى\s*عليه\s*[:\-]?\s*([^\n\r]+)",
                r"جهة\s*[:\-]?\s*([^\n\r]+)",
                r"فرد\s*[:\-]?\s*([^\n\r]+)"
            ],
            "defendant_id": [
                r"رقم\s*هوية\s*المدعى\s*عليه\s*[:\-]?\s*([^\n\r]+)",
                r"هوية\s*المدعى\s*عليه\s*[:\-]?\s*([^\n\r]+)",
                r"([٠١٢٣٤٥٦٧٨٩\d]{10})"
            ],
            "court_name": [
                r"المحكمة\s*[:\-]?\s*([^\n\r]+)",
                r"المحكمة\s*المختصة\s*[:\-]?\s*([^\n\r]+)",
                r"قسم\s*[:\-]?\s*([^\n\r]+)",
                r"court\s*[:\-]?\s*([^\n\r]+)",
                # Enhanced patterns for Saudi legal documents
                r"مقدمة\s*للمحكمة\s*[:\-]?\s*([^\n\r]+)",
                r"المحكمة\s*الإدارية\s*[:\-]?\s*([^\n\r]+)",
                r"المحكمة\s*التجارية\s*[:\-]?\s*([^\n\r]+)",
                r"المحكمة\s*الجنائية\s*[:\-]?\s*([^\n\r]+)",
                r"المحكمة\s*المدنية\s*[:\-]?\s*([^\n\r]+)"
            ],
            "court_type": [
                r"نوع\s*المحكمة\s*[:\-]?\s*([^\n\r]+)",
                r"محكمة\s*[:\-]?\s*([^\n\r]+)",
                r"إدارية|تجارية|جنائية|مدنية"
            ],
            "court_location": [
                r"موقع\s*المحكمة\s*[:\-]?\s*([^\n\r]+)",
                r"الموقع\s*[:\-]?\s*([^\n\r]+)",
                r"location\s*[:\-]?\s*([^\n\r]+)"
            ],
            "case_type": [
                r"(دعوى\s*اداريه)",
                r"(دعوى\s*إدارية)",
                r"(دعوى\s*ادارية)",
                r"نوع\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                r"صنف\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                r"case\s*type\s*[:\-]?\s*([^\n\r]+)"
            ],
            "case_subject": [
                r"موضوع\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                r"الموضوع\s*[:\-]?\s*([^\n\r]+)",
                r"سبب\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                r"subject\s*[:\-]?\s*([^\n\r]+)"
            ],
            "case_facts": [
                r"وقائع\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                r"الوقائع\s*[:\-]?\s*([^\n\r]+)",
                r"case\s*facts\s*[:\-]?\s*([^\n\r]+)"
            ],
            "case_requests": [
                r"الطلب\s*[:\-]?\s*([^\n\r]+)",
                r"طلبات\s*[:\-]?\s*([^\n\r]+)",
                r"ما\s*يطلب\s*[:\-]?\s*([^\n\r]+)",
                r"request\s*[:\-]?\s*([^\n\r]+)"
            ],
            "claim_overview": [
                r"موضوع\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                r"الموضوع\s*[:\-]?\s*([^\n\r]+)",
                r"سبب\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                r"وصف\s*الطلب\s*[:\-]?\s*([^\n\r]+)",
                r"ملخص\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                r"شرح\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                r"تفاصيل\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
                r"subject\s*[:\-]?\s*([^\n\r]+)",
                r"overview\s*[:\-]?\s*([^\n\r]+)",
                r"summary\s*[:\-]?\s*([^\n\r]+)"
            ],
            "decision_number": [
                r"رقم\s*القرار\s*[:\-]?\s*([^\n\r]+)",
                r"القرار\s*[:\-]?\s*([^\n\r]+)",
                r"decision\s*number\s*[:\-]?\s*([^\n\r]+)"
            ],
            "appeal_number": [
                r"رقم\s*التظلم\s*[:\-]?\s*([^\n\r]+)",
                r"التظلم\s*[:\-]?\s*([^\n\r]+)",
                r"appeal\s*number\s*[:\-]?\s*([^\n\r]+)"
            ],
            "violation_number": [
                r"رقم\s*المخالفة\s*[:\-]?\s*([^\n\r]+)",
                r"المخالفة\s*[:\-]?\s*([^\n\r]+)",
                r"violation\s*number\s*[:\-]?\s*([^\n\r]+)"
            ],
            "claim_amount": [
                r"مبلغ\s*المطالبة\s*[:\-]?\s*([^\n\r]+)",
                r"المبلغ\s*[:\-]?\s*([^\n\r]+)",
                r"claim\s*amount\s*[:\-]?\s*([^\n\r]+)",
                r"([٠١٢٣٤٥٦٧٨٩\d,\.]+)\s*ريال"
            ],
            # Saudi legal document specific patterns
            "request_number": [
                r"رقم\s*الطلب\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                r"الطلب\s*رقم\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)"
            ],
            "case_registration_number": [
                r"رقم\s*قيد\s*الدعوى\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                r"قيد\s*الدعوى\s*رقم\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)"
            ],
            "decision_date": [
                r"تاريخ\s*القرار\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\/]+)",
                r"القرار\s*بتاريخ\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\/]+)"
            ],
            "notification_date": [
                r"تاريخ\s*العلم\s*القرار\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\/]+)",
                r"العلم\s*بتاريخ\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\/]+)"
            ],
            "appeal_date": [
                r"تاريخ\s*التظلم\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\/]+)",
                r"التظلم\s*بتاريخ\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\/]+)"
            ],
            "applicant_name": [
                r"مقدم\s*الطلب\s*[:\-]?\s*([^\n\r]+)",
                r"اسم\s*مقدم\s*الطلب\s*[:\-]?\s*([^\n\r]+)",
                r"المتقدم\s*[:\-]?\s*([^\n\r]+)"
            ],
            "primary_mobile": [
                r"رقم\s*الجوال\s*الاساسي\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                r"الجوال\s*الاساسي\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)"
            ],
            "secondary_mobile": [
                r"رقم\s*الجوال\s*الاضافي\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                r"الجوال\s*الاضافي\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)"
            ],
            "contact_email": [
                r"البريد\s*الالكتروني\s*[:\-]?\s*([^\n\r]+)",
                r"الايميل\s*[:\-]?\s*([^\n\r]+)"
            ],
            "national_address": [
                r"العنوان\s*الوطني\s*[:\-]?\s*([^\n\r]+)",
                r"الموقع\s*الوطني\s*[:\-]?\s*([^\n\r]+)"
            ],
            "document_version": [
                r"الاصدار\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                r"النسخة\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)"
            ],
            "reference_code": [
                r"الكود\s*المرجعي\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                r"المرجع\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)"
            ]
        }
    
    async def extract_structured_data(self, raw_text: str) -> Dict[str, Any]:
        """
        Extract structured data from raw text using pattern matching.
        
        Args:
            raw_text: Raw text extracted from document
            
        Returns:
            Dictionary containing extracted structured data
        """
        try:
            logger.info("Starting structured data extraction")
            
            if not raw_text:
                logger.warning("No raw text provided for extraction")
                return {}
            
            # Clean the text
            cleaned_text = self._clean_text(raw_text)
            
            # Extract data using patterns
            extracted_data = {}
            
            for field_name, patterns in self.patterns.items():
                value = self._extract_field_value(cleaned_text, patterns)
                if value:
                    extracted_data[field_name] = value
            
            # Extract Saudi legal document specific fields
            saudi_fields = self._extract_saudi_legal_fields(cleaned_text)
            extracted_data.update(saudi_fields)
            
            # Post-process extracted data
            extracted_data = self._post_process_data(extracted_data)
            
            logger.info(f"Extracted {len(extracted_data)} fields from text")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
            return {}
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for better pattern matching."""
        try:
            # Remove :unselected: markers
            text = text.replace(':unselected:', '')
            
            # Remove excessive whitespace but preserve line breaks for better extraction
            text = re.sub(r'[ \t]+', ' ', text)
            
            # Normalize Arabic text
            text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
            text = text.replace('ة', 'ه')
            
            # Remove special characters but keep Arabic, English, numbers, and basic punctuation
            text = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFFa-zA-Z0-9\s\-:\.@\n\r]', '', text)
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error cleaning text: {e}")
            return text
    
    def _extract_field_value(self, text: str, patterns: List[str]) -> Optional[str]:
        """Extract field value using multiple patterns."""
        try:
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    if value and len(value) > 1:
                        # Clean the extracted value
                        value = self._clean_extracted_value(value)
                        # Limit length to prevent overly long values
                        if len(value) > 50:
                            # Try to find a better boundary (space, comma, etc.)
                            for i in range(50, min(len(value), 100)):
                                if value[i] in [' ', ',', '.', '\n', '\r']:
                                    value = value[:i].strip()
                                    break
                            else:
                                value = value[:50].strip()
                        if value and len(value) > 2:
                            return value
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting field value: {e}")
            return None
    
    def _clean_extracted_value(self, value: str) -> str:
        """Clean extracted value."""
        try:
            # Remove common prefixes/suffixes
            value = value.strip()
            value = re.sub(r'^[:\-\s]+', '', value)
            value = re.sub(r'[:\-\s]+$', '', value)
            
            # Remove excessive whitespace
            value = re.sub(r'\s+', ' ', value)
            
            # Remove common unwanted patterns
            value = re.sub(r'رقم\s*[٠١٢٣٤٥٦٧٨٩\d]+', '', value)
            value = re.sub(r'[٠١٢٣٤٥٦٧٨٩\d]+\s*رقم', '', value)
            
            return value.strip()
            
        except Exception as e:
            logger.error(f"Error cleaning extracted value: {e}")
            return value
    
    def _post_process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process extracted data for better quality."""
        try:
            processed_data = {}
            
            for field, value in data.items():
                if not value or value == "غير مذكور":
                    continue
                
                # Apply field-specific processing
                processed_value = self._process_field_value(field, value)
                if processed_value:
                    processed_data[field] = processed_value
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error post-processing data: {e}")
            return data
    
    def _process_field_value(self, field: str, value: str) -> Optional[str]:
        """Apply field-specific processing to extracted values."""
        try:
            if field in ["plaintiff_mobile", "plaintiff_id", "defendant_id"]:
                # Ensure numeric fields contain only digits
                if not re.match(r'^[\d٠١٢٣٤٥٦٧٨٩]+$', value):
                    return None
            
            elif field == "plaintiff_email":
                # Validate email format
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
                    return None
            
            elif field == "filing_date":
                # Normalize date format
                value = self._normalize_date(value)
            
            elif field == "claim_amount":
                # Extract numeric amount
                amount_match = re.search(r'([٠١٢٣٤٥٦٧٨٩\d,\.]+)', value)
                if amount_match:
                    value = amount_match.group(1)
            
            return value if value and len(value) > 1 else None
            
        except Exception as e:
            logger.error(f"Error processing field value {field}: {e}")
            return None
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date format."""
        try:
            # Convert Arabic numerals to English
            arabic_to_english = {
                '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
                '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
            }
            
            for arabic, english in arabic_to_english.items():
                date_str = date_str.replace(arabic, english)
            
            return date_str
            
        except Exception as e:
            logger.error(f"Error normalizing date: {e}")
            return date_str
    
    def extract_text_sections(self, raw_text: str) -> Dict[str, str]:
        """Extract different sections of the document text."""
        try:
            sections = {
                "header": "",
                "parties": "",
                "case_details": "",
                "requests": "",
                "footer": ""
            }
            
            lines = raw_text.split('\n')
            current_section = "header"
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Determine section based on keywords
                if any(keyword in line for keyword in ["صحيفة دعوى", "بيانات صحيفة الدعوى"]):
                    current_section = "header"
                elif any(keyword in line for keyword in ["المدعي", "المدعى عليه", "الخصم", "مقدم الطلب"]):
                    current_section = "parties"
                elif any(keyword in line for keyword in ["موضوع", "وقائع", "نوع الدعوى"]):
                    current_section = "case_details"
                elif any(keyword in line for keyword in ["الطلب", "طلبات", "ما يطلب", "الطلبات المقدمة"]):
                    current_section = "requests"
                elif any(keyword in line for keyword in ["التاريخ", "التوقيع", "الختم"]):
                    current_section = "footer"
                
                sections[current_section] += line + "\n"
            
            return sections
            
        except Exception as e:
            logger.error(f"Error extracting text sections: {e}")
            return {"header": raw_text, "parties": "", "case_details": "", "requests": "", "footer": ""}
    
    def extract_saudi_legal_sections(self, raw_text: str) -> Dict[str, str]:
        """Extract sections specific to Saudi legal documents."""
        try:
            sections = {
                "document_header": "",
                "case_statement_data": "",
                "national_address": "",
                "additional_info": "",
                "requests_in_case": "",
                "declarations": "",
                "required_documents": "",
                "contact_info": "",
                "document_footer": ""
            }
            
            lines = raw_text.split('\n')
            current_section = "document_header"
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Determine section based on Saudi legal document keywords
                if any(keyword in line for keyword in ["المملكة العربية السعودية", "ديوان المظالم", "المحكمة الإدارية"]):
                    current_section = "document_header"
                elif any(keyword in line for keyword in ["بيانات صحيفة الدعوى", "رقم الطلب", "رقم قيد الدعوى"]):
                    current_section = "case_statement_data"
                elif any(keyword in line for keyword in ["العنوان الوطني"]):
                    current_section = "national_address"
                elif any(keyword in line for keyword in ["معلومات اضافية", "رقم القرار", "رقم التظلم"]):
                    current_section = "additional_info"
                elif any(keyword in line for keyword in ["الطلبات المقدمة في القضية", "وصف الطلب"]):
                    current_section = "requests_in_case"
                elif any(keyword in line for keyword in ["الاقرارات", "أتعهد", "أقر"]):
                    current_section = "declarations"
                elif any(keyword in line for keyword in ["المستندات الواجب ارفاقها", "صورة هوية"]):
                    current_section = "required_documents"
                elif any(keyword in line for keyword in ["بيانات التواصل", "رقم الجوال", "البريد الالكتروني"]):
                    current_section = "contact_info"
                elif any(keyword in line for keyword in ["الاصدار", "تاريخ الاصدار", "الكود المرجعي"]):
                    current_section = "document_footer"
                
                sections[current_section] += line + "\n"
            
            return sections
            
        except Exception as e:
            logger.error(f"Error extracting Saudi legal sections: {e}")
            return {"document_header": raw_text, "case_statement_data": "", "additional_info": "", "requests_in_case": "", "declarations": "", "required_documents": "", "contact_info": "", "document_footer": ""}
    
    def _extract_saudi_legal_fields(self, text: str) -> Dict[str, Any]:
        """Extract Saudi legal document specific fields."""
        try:
            saudi_fields = {}
            
            # Extract Saudi-specific patterns
            saudi_patterns = {
                "request_number": [
                    r"رقم\s*الطلب\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                    r"الطلب\s*رقم\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)"
                ],
                "case_registration_number": [
                    r"رقم\s*قيد\s*الدعوى\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                    r"قيد\s*الدعوى\s*رقم\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)"
                ],
                "decision_date": [
                    r"تاريخ\s*القرار\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\/]+)",
                    r"القرار\s*بتاريخ\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\/]+)"
                ],
                "notification_date": [
                    r"تاريخ\s*العلم\s*القرار\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\/]+)",
                    r"العلم\s*بتاريخ\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\/]+)"
                ],
                "appeal_date": [
                    r"تاريخ\s*التظلم\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\/]+)",
                    r"التظلم\s*بتاريخ\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\/]+)"
                ],
                "applicant_name": [
                    r"مقدم\s*الطلب\s*[:\-]?\s*([^\n\r]+)",
                    r"اسم\s*مقدم\s*الطلب\s*[:\-]?\s*([^\n\r]+)",
                    r"المتقدم\s*[:\-]?\s*([^\n\r]+)"
                ],
                "primary_mobile": [
                    r"رقم\s*الجوال\s*الاساسي\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                    r"الجوال\s*الاساسي\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)"
                ],
                "secondary_mobile": [
                    r"رقم\s*الجوال\s*الاضافي\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                    r"الجوال\s*الاضافي\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)"
                ],
                "contact_email": [
                    r"البريد\s*الالكتروني\s*[:\-]?\s*([^\n\r]+)",
                    r"الايميل\s*[:\-]?\s*([^\n\r]+)"
                ],
                "national_address": [
                    r"العنوان\s*الوطني\s*[:\-]?\s*([^\n\r]+)",
                    r"الموقع\s*الوطني\s*[:\-]?\s*([^\n\r]+)"
                ],
                "document_version": [
                    r"الاصدار\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                    r"النسخة\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)"
                ],
                "reference_code": [
                    r"الكود\s*المرجعي\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)",
                    r"المرجع\s*[:\-]?\s*([٠١٢٣٤٥٦٧٨٩\d]+)"
                ]
            }
            
            for field_name, patterns in saudi_patterns.items():
                value = self._extract_field_value(text, patterns)
                if value:
                    saudi_fields[field_name] = value
            
            return saudi_fields
            
        except Exception as e:
            logger.error(f"Error extracting Saudi legal fields: {e}")
            return {} 