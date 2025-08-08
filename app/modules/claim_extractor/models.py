"""
Data Models for Claim Extractor Module

This module defines the data structures used for claim extraction and processing.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
import re


class ProcessingStatus(str, Enum):
    """Status of claim processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATED = "validated"
    INVALID = "invalid"


class PageContent(BaseModel):
    """Content extracted from a single page."""
    
    page_number: int = Field(..., description="رقم الصفحة")
    extracted_text: str = Field(..., description="النص المستخرج من الصفحة")
    confidence: float = Field(0.0, description="مستوى الثقة في الاستخراج")
    model_used: Optional[str] = Field(None, description="النموذج المستخدم للاستخراج")
    processing_time: Optional[float] = Field(None, description="وقت معالجة الصفحة بالثواني")
    key_value_pairs: Dict[str, str] = Field(default_factory=dict, description="أزواج المفاتيح والقيم")
    form_fields: Dict[str, str] = Field(default_factory=dict, description="حقول النموذج")
    success: bool = Field(True, description="نجح استخراج الصفحة")
    error_message: Optional[str] = Field(None, description="رسالة الخطأ إن وجدت")


class ClaimInfo(BaseModel):
    """Structured claim information extracted from documents."""
    
    # Basic claim information
    case_number: Optional[str] = Field(None, description="رقم القضية")
    claim_number: Optional[str] = Field(None, description="رقم الطلب")
    filing_date: Optional[str] = Field(None, description="تاريخ رفع الدعوى")
    
    # Parties information
    plaintiff_name: Optional[str] = Field(None, description="اسم المدعي")
    plaintiff_id: Optional[str] = Field(None, description="رقم هوية المدعي")
    plaintiff_mobile: Optional[str] = Field(None, description="رقم جوال المدعي")
    plaintiff_email: Optional[str] = Field(None, description="البريد الإلكتروني للمدعي")
    plaintiff_address: Optional[str] = Field(None, description="عنوان المدعي")
    
    defendant_name: Optional[str] = Field(None, description="اسم المدعى عليه")
    defendant_type: Optional[str] = Field(None, description="نوع المدعى عليه (فرد/جهة)")
    defendant_id: Optional[str] = Field(None, description="رقم هوية المدعى عليه")
    
    # Court information
    court_name: Optional[str] = Field(None, description="اسم المحكمة")
    court_type: Optional[str] = Field(None, description="نوع المحكمة")
    court_location: Optional[str] = Field(None, description="موقع المحكمة")
    
    # Case details
    case_type: Optional[str] = Field(None, description="نوع الدعوى")
    case_subject: Optional[str] = Field(None, description="موضوع الدعوى")
    case_facts: Optional[str] = Field(None, description="وقائع الدعوى")
    case_requests: Optional[str] = Field(None, description="طلبات الدعوى")
    claim_overview: Optional[str] = Field(None, description="ملخص الدعوى - شرح مبسط للمستخدم")
    
    # Additional information
    decision_number: Optional[str] = Field(None, description="رقم القرار")
    appeal_number: Optional[str] = Field(None, description="رقم التظلم")
    violation_number: Optional[str] = Field(None, description="رقم المخالفة")
    
    # Saudi legal document specific fields
    request_number: Optional[str] = Field(None, description="رقم الطلب")
    case_registration_number: Optional[str] = Field(None, description="رقم قيد الدعوى")
    decision_date: Optional[str] = Field(None, description="تاريخ القرار")
    notification_date: Optional[str] = Field(None, description="تاريخ العلم بالقرار")
    appeal_date: Optional[str] = Field(None, description="تاريخ التظلم")
    applicant_name: Optional[str] = Field(None, description="اسم مقدم الطلب")
    primary_mobile: Optional[str] = Field(None, description="رقم الجوال الأساسي")
    secondary_mobile: Optional[str] = Field(None, description="رقم الجوال الإضافي")
    contact_email: Optional[str] = Field(None, description="البريد الإلكتروني")
    national_address: Optional[str] = Field(None, description="العنوان الوطني")
    document_version: Optional[str] = Field(None, description="إصدار المستند")
    reference_code: Optional[str] = Field(None, description="الكود المرجعي")
    
    # Financial information
    claim_amount: Optional[str] = Field(None, description="مبلغ المطالبة")
    currency: Optional[str] = Field("ريال سعودي", description="عملة المطالبة")
    
    # Document metadata
    document_type: Optional[str] = Field(None, description="نوع المستند")
    total_pages: Optional[int] = Field(None, description="عدد الصفحات")
    processing_confidence: Optional[float] = Field(None, description="مستوى الثقة في الاستخراج")
    
    # Validation
    is_valid: bool = Field(False, description="هل المستند صالح")
    validation_errors: List[str] = Field(default_factory=list, description="أخطاء التحقق")
    
    @validator('plaintiff_mobile', 'defendant_id', 'plaintiff_id')
    def validate_numeric_fields(cls, v):
        """Validate numeric fields contain only digits."""
        if v and not re.match(r'^[\d٠١٢٣٤٥٦٧٨٩]+$', v):
            return None
        return v
    
    @validator('plaintiff_email')
    def validate_email(cls, v):
        """Validate email format."""
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            return None
        return v
    
    @validator('processing_confidence')
    def validate_confidence(cls, v):
        """Validate confidence is between 0 and 1."""
        if v is not None and (v < 0 or v > 1):
            return 0.0
        return v
    
    def get_validation_score(self) -> float:
        """Calculate validation score based on completeness."""
        required_fields = [
            'plaintiff_name', 'defendant_name', 'case_type', 
            'case_subject', 'claim_overview'
        ]
        
        filled_fields = sum(1 for field in required_fields if getattr(self, field))
        return filled_fields / len(required_fields) if required_fields else 0.0
    
    def is_complete(self) -> bool:
        """Check if claim information is complete."""
        return self.get_validation_score() >= 0.7


class ExtractionResult(BaseModel):
    """Result of claim extraction process."""
    
    # Processing information
    status: ProcessingStatus = Field(ProcessingStatus.PENDING, description="حالة المعالجة")
    processing_id: str = Field(..., description="معرف المعالجة")
    filename: str = Field(..., description="اسم الملف")
    file_url: Optional[str] = Field(None, description="رابط الملف في التخزين")
    
    # Extraction results
    raw_text: Optional[str] = Field(None, description="النص المستخرج (مدمج)")
    raw_text_length: Optional[int] = Field(None, description="طول النص المستخرج")
    page_contents: List[PageContent] = Field(default_factory=list, description="محتوى كل صفحة منفصلة")
    extracted_claim: Optional[ClaimInfo] = Field(None, description="معلومات الدعوى المستخرجة")
    refined_response: Optional[str] = Field(None, description="الرد المحسن")
    
    # Processing metadata
    processing_time: Optional[float] = Field(None, description="وقت المعالجة بالثواني")
    document_intelligence_confidence: Optional[float] = Field(None, description="ثقة ذكاء المستندات")
    openai_confidence: Optional[float] = Field(None, description="ثقة الذكاء الاصطناعي")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="رسالة الخطأ")
    error_details: Optional[Dict[str, Any]] = Field(None, description="تفاصيل الخطأ")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="وقت الإنشاء")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="وقت التحديث")
    completed_at: Optional[datetime] = Field(None, description="وقت الإكمال")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def update_status(self, status: ProcessingStatus, error_message: Optional[str] = None):
        """Update processing status."""
        self.status = status
        self.updated_at = datetime.utcnow()
        
        if status in [ProcessingStatus.COMPLETED, ProcessingStatus.VALIDATED, ProcessingStatus.INVALID]:
            self.completed_at = datetime.utcnow()
        
        if error_message:
            self.error_message = error_message
    
    def add_error(self, error: str, details: Optional[Dict[str, Any]] = None):
        """Add error information."""
        self.error_message = error
        if details:
            self.error_details = details
        self.update_status(ProcessingStatus.FAILED, error)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "status": self.status.value,
            "processing_id": self.processing_id,
            "filename": self.filename,
            "file_url": self.file_url,
            "raw_text": self.raw_text,
            "raw_text_length": self.raw_text_length,
            "page_contents": [page.dict() for page in self.page_contents],
            "extracted_claim": self.extracted_claim.dict() if self.extracted_claim else None,
            "refined_response": self.refined_response,
            "processing_time": self.processing_time,
            "document_intelligence_confidence": self.document_intelligence_confidence,
            "openai_confidence": self.openai_confidence,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractionResult":
        """Create from dictionary."""
        # Convert page_contents back to PageContent objects
        page_contents = []
        if data.get("page_contents"):
            for page_data in data["page_contents"]:
                page_contents.append(PageContent(**page_data))
        
        # Convert extracted_claim back to ClaimInfo object
        extracted_claim = None
        if data.get("extracted_claim"):
            extracted_claim = ClaimInfo(**data["extracted_claim"])
        
        # Convert status back to enum
        status = ProcessingStatus(data.get("status", "pending"))
        
        return cls(
            status=status,
            processing_id=data["processing_id"],
            filename=data["filename"],
            file_url=data.get("file_url"),
            raw_text=data.get("raw_text"),
            raw_text_length=data.get("raw_text_length"),
            page_contents=page_contents,
            extracted_claim=extracted_claim,
            refined_response=data.get("refined_response"),
            processing_time=data.get("processing_time"),
            document_intelligence_confidence=data.get("document_intelligence_confidence"),
            openai_confidence=data.get("openai_confidence"),
            error_message=data.get("error_message"),
            error_details=data.get("error_details"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        ) 