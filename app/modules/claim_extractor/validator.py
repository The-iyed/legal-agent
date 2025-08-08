"""
Claim Validator for Claim Extractor

This module validates extracted claim information and provides
confidence scores and validation results.
"""

import logging
import re
from typing import List, Dict, Any
from dataclasses import dataclass

from .models import ClaimInfo

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of claim validation."""
    is_valid: bool
    confidence: float
    errors: List[str]
    warnings: List[str]
    score: float


class ClaimValidator:
    """Validates extracted claim information."""
    
    def __init__(self):
        self.required_fields = [
            'case_number', 'plaintiff_name', 'defendant_name', 
            'court_name', 'case_type', 'case_subject'
        ]
        
        self.important_fields = [
            'filing_date', 'plaintiff_mobile', 'plaintiff_email',
            'case_facts', 'case_requests'
        ]
        
        logger.info("ClaimValidator initialized")
    
    async def validate_claim(self, claim_info: ClaimInfo) -> ValidationResult:
        """
        Validate extracted claim information.
        
        Args:
            claim_info: Extracted claim information to validate
            
        Returns:
            ValidationResult with validation details
        """
        try:
            logger.info("Starting claim validation")
            
            errors = []
            warnings = []
            score = 0.0
            
            # Validate required fields
            required_score = self._validate_required_fields(claim_info, errors)
            
            # Validate field formats
            format_score = self._validate_field_formats(claim_info, errors, warnings)
            
            # Validate field consistency
            consistency_score = self._validate_field_consistency(claim_info, warnings)
            
            # Calculate overall score
            score = (required_score * 0.5) + (format_score * 0.3) + (consistency_score * 0.2)
            
            # Determine if claim is valid
            is_valid = len(errors) == 0 and score >= 0.7
            
            # Calculate confidence
            confidence = min(score, 1.0)
            
            result = ValidationResult(
                is_valid=is_valid,
                confidence=confidence,
                errors=errors,
                warnings=warnings,
                score=score
            )
            
            logger.info(f"Claim validation completed. Score: {score:.2f}, Valid: {is_valid}")
            return result
            
        except Exception as e:
            logger.error(f"Error validating claim: {e}")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                score=0.0
            )
    
    def _validate_required_fields(self, claim_info: ClaimInfo, errors: List[str]) -> float:
        """Validate that all required fields are present."""
        try:
            filled_fields = 0
            total_fields = len(self.required_fields)
            
            for field in self.required_fields:
                value = getattr(claim_info, field, None)
                if value and value.strip() and value != "غير مذكور":
                    filled_fields += 1
                else:
                    errors.append(f"الحقل المطلوب مفقود: {field}")
            
            score = filled_fields / total_fields if total_fields > 0 else 0.0
            return score
            
        except Exception as e:
            logger.error(f"Error validating required fields: {e}")
            return 0.0
    
    def _validate_field_formats(self, claim_info: ClaimInfo, errors: List[str], warnings: List[str]) -> float:
        """Validate field formats and patterns."""
        try:
            format_score = 0.0
            total_checks = 0
            
            # Validate mobile number
            if claim_info.plaintiff_mobile:
                total_checks += 1
                if self._is_valid_mobile(claim_info.plaintiff_mobile):
                    format_score += 1
                else:
                    warnings.append("رقم الجوال غير صحيح")
            
            # Validate email
            if claim_info.plaintiff_email:
                total_checks += 1
                if self._is_valid_email(claim_info.plaintiff_email):
                    format_score += 1
                else:
                    warnings.append("البريد الإلكتروني غير صحيح")
            
            # Validate ID numbers
            if claim_info.plaintiff_id:
                total_checks += 1
                if self._is_valid_id(claim_info.plaintiff_id):
                    format_score += 1
                else:
                    warnings.append("رقم هوية المدعي غير صحيح")
            
            if claim_info.defendant_id:
                total_checks += 1
                if self._is_valid_id(claim_info.defendant_id):
                    format_score += 1
                else:
                    warnings.append("رقم هوية المدعى عليه غير صحيح")
            
            # Validate case number
            if claim_info.case_number:
                total_checks += 1
                if self._is_valid_case_number(claim_info.case_number):
                    format_score += 1
                else:
                    warnings.append("رقم القضية غير صحيح")
            
            # Validate date format
            if claim_info.filing_date:
                total_checks += 1
                if self._is_valid_date(claim_info.filing_date):
                    format_score += 1
                else:
                    warnings.append("تاريخ رفع الدعوى غير صحيح")
            
            return format_score / total_checks if total_checks > 0 else 1.0
            
        except Exception as e:
            logger.error(f"Error validating field formats: {e}")
            return 0.0
    
    def _validate_field_consistency(self, claim_info: ClaimInfo, warnings: List[str]) -> float:
        """Validate consistency between fields."""
        try:
            consistency_score = 1.0
            total_checks = 0
            
            # Check if plaintiff and defendant are different
            if claim_info.plaintiff_name and claim_info.defendant_name:
                total_checks += 1
                if claim_info.plaintiff_name.strip() == claim_info.defendant_name.strip():
                    warnings.append("اسم المدعي واسم المدعى عليه متطابقان")
                    consistency_score -= 0.2
            
            # Check if case type matches court type
            if claim_info.case_type and claim_info.court_type:
                total_checks += 1
                if not self._is_case_court_consistent(claim_info.case_type, claim_info.court_type):
                    warnings.append("نوع الدعوى لا يتطابق مع نوع المحكمة")
                    consistency_score -= 0.1
            
            # Check if claim amount is reasonable
            if claim_info.claim_amount:
                total_checks += 1
                if not self._is_reasonable_amount(claim_info.claim_amount):
                    warnings.append("مبلغ المطالبة غير معقول")
                    consistency_score -= 0.1
            
            return consistency_score if total_checks > 0 else 1.0
            
        except Exception as e:
            logger.error(f"Error validating field consistency: {e}")
            return 1.0
    
    def _is_valid_mobile(self, mobile: str) -> bool:
        """Validate mobile number format."""
        try:
            # Remove any non-digit characters
            digits_only = re.sub(r'[^\d٠١٢٣٤٥٦٧٨٩]', '', mobile)
            
            # Check if it's a valid Saudi mobile number
            if len(digits_only) == 10:
                # Saudi mobile numbers start with 05
                if digits_only.startswith('05'):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating mobile: {e}")
            return False
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format."""
        try:
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(pattern, email))
            
        except Exception as e:
            logger.error(f"Error validating email: {e}")
            return False
    
    def _is_valid_id(self, id_number: str) -> bool:
        """Validate Saudi ID number format."""
        try:
            # Remove any non-digit characters
            digits_only = re.sub(r'[^\d٠١٢٣٤٥٦٧٨٩]', '', id_number)
            
            # Saudi ID numbers are 10 digits
            return len(digits_only) == 10
            
        except Exception as e:
            logger.error(f"Error validating ID: {e}")
            return False
    
    def _is_valid_case_number(self, case_number: str) -> bool:
        """Validate case number format."""
        try:
            # Case numbers should contain digits
            digits = re.findall(r'[\d٠١٢٣٤٥٦٧٨٩]', case_number)
            return len(digits) >= 3
            
        except Exception as e:
            logger.error(f"Error validating case number: {e}")
            return False
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Validate date format."""
        try:
            # Check for common date patterns
            patterns = [
                r'\d{4}/\d{2}/\d{2}',
                r'\d{4}-\d{2}-\d{2}',
                r'\d{2}/\d{2}/\d{4}',
                r'\d{2}-\d{2}-\d{4}'
            ]
            
            for pattern in patterns:
                if re.search(pattern, date_str):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating date: {e}")
            return False
    
    def _is_case_court_consistent(self, case_type: str, court_type: str) -> bool:
        """Check if case type is consistent with court type."""
        try:
            case_type_lower = case_type.lower()
            court_type_lower = court_type.lower()
            
            # Define consistency rules
            consistency_rules = {
                'إدارية': ['إدارية', 'administrative'],
                'تجارية': ['تجارية', 'commercial'],
                'جنائية': ['جنائية', 'criminal'],
                'مدنية': ['مدنية', 'civil']
            }
            
            for court_category, case_types in consistency_rules.items():
                if court_category in court_type_lower:
                    return any(ct in case_type_lower for ct in case_types)
            
            return True  # If no specific rule matches, assume consistent
            
        except Exception as e:
            logger.error(f"Error checking case-court consistency: {e}")
            return True
    
    def _is_reasonable_amount(self, amount: str) -> bool:
        """Check if claim amount is reasonable."""
        try:
            # Extract numeric value
            numeric_match = re.search(r'([\d٠١٢٣٤٥٦٧٨٩,\.]+)', amount)
            if not numeric_match:
                return False
            
            # Convert Arabic numerals to English
            numeric_str = numeric_match.group(1)
            arabic_to_english = {
                '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
                '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
            }
            
            for arabic, english in arabic_to_english.items():
                numeric_str = numeric_str.replace(arabic, english)
            
            # Remove commas and convert to float
            numeric_str = numeric_str.replace(',', '')
            try:
                amount_value = float(numeric_str)
                
                # Check if amount is reasonable (between 1 and 100 million SAR)
                return 1 <= amount_value <= 100000000
                
            except ValueError:
                return False
            
        except Exception as e:
            logger.error(f"Error checking amount reasonableness: {e}")
            return True
    
    def get_validation_summary(self, validation_result: ValidationResult) -> Dict[str, Any]:
        """Get a summary of validation results."""
        try:
            return {
                "is_valid": validation_result.is_valid,
                "confidence": validation_result.confidence,
                "score": validation_result.score,
                "error_count": len(validation_result.errors),
                "warning_count": len(validation_result.warnings),
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "quality_level": self._get_quality_level(validation_result.score)
            }
            
        except Exception as e:
            logger.error(f"Error getting validation summary: {e}")
            return {
                "is_valid": False,
                "confidence": 0.0,
                "score": 0.0,
                "error_count": 1,
                "warning_count": 0,
                "errors": ["Error generating validation summary"],
                "warnings": [],
                "quality_level": "poor"
            }
    
    def _get_quality_level(self, score: float) -> str:
        """Get quality level based on validation score."""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.8:
            return "good"
        elif score >= 0.7:
            return "acceptable"
        elif score >= 0.5:
            return "poor"
        else:
            return "very_poor" 