from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, List

class QueryRequest(BaseModel):
    conversation_id: str
    user_id: str
    query: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": "507f1f77bcf86cd799439011",
                "user_id": "user123",
                "query": "What is the weather like?"
            }
        }
    )

class QueryResponse(BaseModel):
    response: str
    metadata: Optional[dict[str, Any]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "response": "The weather in New York is sunny with a temperature of 72°F.",
                "metadata": {
                    "confidence": 0.95,
                    "sources": ["weather_api"]
                }
            }
        }
    )

class FileUploadRequest(BaseModel):
    conversation_id: str
    user_id: str
    file: Any  # This will be handled by FastAPI's File upload

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": "507f1f77bcf86cd799439011",
                "user_id": "user123"
            }
        }
    )

class ExtractedField(BaseModel):
    field_name: str
    field_name_arabic: str
    field_value: str
    confidence: float
    page_number: int
    bounding_box: Optional[dict] = None
    field_type: str = "text"
    is_required: bool = True
    validation_rules: Optional[List[str]] = None

class StatementOfClaim(BaseModel):
    conversation_id: str
    document_id: str
    document_type: str
    extracted_fields: List[ExtractedField]
    validation_score: float
    is_valid: bool
    validation_errors: List[str]
    extraction_timestamp: str
    total_pages: int
    processing_status: str
    raw_text: str
    file_url: str
    extraction_method: str
    ai_validation_score: float
    ai_validation_errors: List[str]
    created_at: str
    updated_at: str

class FileUploadResponse(BaseModel):
    response: str
    file_url: str
    case_number: Optional[str] = None
    is_valid: bool
    metadata: dict[str, Any]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "response": "تم التحقق من صحة المستند بنجاح. هل لديك مرفقات تريد رفعها؟",
                "file_url": "https://storage.blob.core.windows.net/leg-files/conversation_id/file.pdf",
                "case_number": "1383951",
                "is_valid": True,
                "metadata": {
                    "document_type": "بيانات صحيفة الدعوى",
                    "validation_score": 0.78,
                    "validation_errors": [],
                    "total_pages": 1
                }
            }
        }
    )

class FileInfoResponse(BaseModel):
    conversation_id: str
    file_url: str
    filename: str
    content_type: str
    size: int
    created_at: str
    last_modified: str
    metadata: dict[str, Any]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": "507f1f77bcf86cd799439011",
                "file_url": "https://storage.blob.core.windows.net/leg-files/conversation_id/file.pdf",
                "filename": "صحيفة الدعوى.pdf",
                "content_type": "application/pdf",
                "size": 268387,
                "created_at": "2024-03-20T10:00:00Z",
                "last_modified": "2024-03-20T10:00:00Z",
                "metadata": {
                    "document_type": "بيانات صحيفة الدعوى",
                    "validation_score": 0.78,
                    "total_pages": 1
                }
            }
        }
    ) 