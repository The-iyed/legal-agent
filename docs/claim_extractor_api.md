# Claim Extractor API Documentation

This document describes the dedicated API endpoints for testing and using the claim extractor module functionality.

## Base URL

```
http://localhost:8000/api/v1/claim-extractor
```

## Endpoints Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check for all components |
| `/sample-data` | GET | Get sample data for testing |
| `/process-text` | POST | Process raw text to extract structured data |
| `/validate` | POST | Validate extracted claim information |
| `/refine` | POST | Refine information using Azure OpenAI |
| `/upload-test` | POST | Test file upload to Azure Blob Storage |
| `/extract` | POST | Complete claim extraction from PDF |

## 1. Health Check

### GET `/health`

Check the health status of all claim extractor components.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2025-08-07T15:39:11.123456",
    "components": {
        "claim_extractor_service": "healthy",
        "text_processor": "healthy",
        "openai_refiner": "healthy",
        "storage_manager": "healthy",
        "validator": "healthy"
    },
    "services": {
        "azure_document_intelligence": "available",
        "azure_openai": "available",
        "azure_storage": "available"
    }
}
```

**Usage:**
```bash
curl http://localhost:8000/api/v1/claim-extractor/health
```

## 2. Sample Data

### GET `/sample-data`

Get sample claim data for testing purposes.

**Response:**
```json
{
    "sample_claim": {
        "case_number": "1383951",
        "plaintiff_name": "عبير احمد سعيد العمودي",
        "defendant_name": "أمانة منطقة الرياض",
        "court_name": "المحكمة الإدارية بالرياض",
        "case_type": "دعوى إدارية",
        "case_subject": "طلب إلغاء قرار إداري",
        "plaintiff_mobile": "0548006700",
        "plaintiff_email": "maabeer@gmail.com"
    },
    "sample_text": "صحيفة الدعوى\n\nبيانات صحيفة الدعوى:\nرقم الطلب: ١٣٨٣٩٥١\n...",
    "usage_examples": {
        "process_text": "POST /api/v1/claim-extractor/process-text with sample_text",
        "validate": "POST /api/v1/claim-extractor/validate with sample_claim",
        "refine": "POST /api/v1/claim-extractor/refine with sample_text and sample_claim",
        "extract": "POST /api/v1/claim-extractor/extract with a PDF file"
    }
}
```

**Usage:**
```bash
curl http://localhost:8000/api/v1/claim-extractor/sample-data
```

## 3. Text Processing

### POST `/process-text`

Process raw text to extract structured claim information.

**Request Body:**
```json
{
    "text": "صحيفة الدعوى\n\nبيانات صحيفة الدعوى:\nرقم الطلب: ١٣٨٣٩٥١\n..."
}
```

**Response:**
```json
{
    "status": "success",
    "extracted_fields": 11,
    "field_names": ["case_number", "plaintiff_name", "defendant_name", "court_name"],
    "structured_data": {
        "case_number": "1383951",
        "plaintiff_name": "عبير احمد سعيد العمودي",
        "defendant_name": "أمانة منطقة الرياض",
        "court_name": "المحكمة الإدارية بالرياض"
    },
    "sections": {
        "header": "صحيفة الدعوى\n\nبيانات صحيفة الدعوى:",
        "parties": "اسم المدعي: عبير احمد سعيد العمودي\nاسم المدعى عليه: أمانة منطقة الرياض",
        "case_details": "نوع الدعوى: دعوى إدارية\nموضوع الدعوى: طلب إلغاء قرار إداري"
    },
    "sections_count": 5
}
```

**Usage:**
```bash
curl -X POST http://localhost:8000/api/v1/claim-extractor/process-text \
  -H "Content-Type: application/json" \
  -d '{"text": "صحيفة الدعوى\nرقم الطلب: 1383951\nاسم المدعي: عبير احمد سعيد العمودي"}'
```

## 4. Claim Validation

### POST `/validate`

Validate extracted claim information.

**Request Body:**
```json
{
    "case_number": "1383951",
    "plaintiff_name": "عبير احمد سعيد العمودي",
    "defendant_name": "أمانة منطقة الرياض",
    "court_name": "المحكمة الإدارية بالرياض",
    "case_type": "دعوى إدارية",
    "case_subject": "طلب إلغاء قرار إداري",
    "plaintiff_mobile": "0548006700",
    "plaintiff_email": "maabeer@gmail.com"
}
```

**Response:**
```json
{
    "status": "success",
    "validation_result": {
        "is_valid": true,
        "confidence": 0.95,
        "score": 0.95,
        "errors": [],
        "warnings": []
    },
    "summary": {
        "is_valid": true,
        "confidence": 0.95,
        "score": 0.95,
        "error_count": 0,
        "warning_count": 0,
        "quality_level": "excellent"
    },
    "claim_info": {
        "case_number": "1383951",
        "plaintiff_name": "عبير احمد سعيد العمودي",
        "defendant_name": "أمانة منطقة الرياض",
        "court_name": "المحكمة الإدارية بالرياض",
        "is_valid": true,
        "validation_errors": []
    }
}
```

**Usage:**
```bash
curl -X POST http://localhost:8000/api/v1/claim-extractor/validate \
  -H "Content-Type: application/json" \
  -d '{
    "case_number": "1383951",
    "plaintiff_name": "عبير احمد سعيد العمودي",
    "defendant_name": "أمانة منطقة الرياض",
    "court_name": "المحكمة الإدارية بالرياض"
  }'
```

## 5. OpenAI Refinement

### POST `/refine`

Refine extracted information using Azure OpenAI.

**Request Body:**
```json
{
    "raw_text": "صحيفة الدعوى\n\nبيانات صحيفة الدعوى:\nرقم الطلب: ١٣٨٣٩٥١\n...",
    "extracted_claim": {
        "case_number": "1383951",
        "plaintiff_name": "عبير احمد سعيد العمودي",
        "defendant_name": "أمانة منطقة الرياض",
        "court_name": "المحكمة الإدارية بالرياض"
    }
}
```

**Response:**
```json
{
    "status": "success",
    "refined_response": "## تحليل صحيفة الدعوى\n\n### ملخص المستند\nتم استخراج معلومات من صحيفة دعوى تحتوي على 1 صفحة...",
    "refined_response_length": 1250,
    "legal_summary": "ملخص قانوني مختصر للدعوى...",
    "legal_summary_length": 300,
    "enhanced_analysis": {
        "enhancement": "تحليل قانوني شامل للمطالبة...",
        "insights": ["تحليل قانوني شامل", "تقييم قوة المطالبة", "متطلبات قانونية"]
    },
    "openai_available": true
}
```

**Usage:**
```bash
curl -X POST http://localhost:8000/api/v1/claim-extractor/refine \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "صحيفة الدعوى\nرقم الطلب: 1383951",
    "extracted_claim": {
        "case_number": "1383951",
        "plaintiff_name": "عبير احمد سعيد العمودي"
    }
  }'
```

## 6. File Upload Test

### POST `/upload-test`

Test file upload to Azure Blob Storage.

**Request:**
- `file`: PDF file to upload
- `conversation_id` (optional): Conversation ID for organization

**Response:**
```json
{
    "status": "success",
    "filename": "test_claim.pdf",
    "file_url": "https://storage.blob.core.windows.net/legal-storage/claims/test_conversation/20250807_163922_e749b33d-35a6-466f-afd6-af2f5fafe590.pdf",
    "file_size": 1796,
    "metadata": {
        "size": 1796,
        "content_type": "application/octet-stream",
        "last_modified": "2025-08-07T15:39:11.000000Z"
    },
    "files_count": 1,
    "storage_available": true,
    "storage_info": {
        "storage_available": true,
        "container_name": "legal-storage",
        "connection_string_configured": true
    }
}
```

**Usage:**
```bash
curl -X POST http://localhost:8000/api/v1/claim-extractor/upload-test \
  -F "file=@test_claim.pdf" \
  -F "conversation_id=test_conversation_123"
```

## 7. Complete Extraction

### POST `/extract`

Complete claim extraction from PDF file.

**Request:**
- `file`: PDF file to process
- `conversation_id` (optional): Conversation ID for organization

**Response:**
```json
{
    "status": "success",
    "processing_id": "2100e117-db79-4728-89f9-ebf216d0656a",
    "filename": "test_claim.pdf",
    "extraction_status": "completed",
    "processing_time": 14.10,
    "file_url": "https://storage.blob.core.windows.net/legal-storage/claims/test_conversation/20250807_163924_6348f7e3-9e74-4f8d-9d20-6faa1525cd90.pdf",
    "raw_text": "Sample Document",
    "raw_text_length": 33,
    "refined_response": "## تحليل صحيفة الدعوى\n\n### ملخص المستند\nتم استخراج معلومات من صحيفة دعوى...",
    "refined_response_length": 611,
    "document_intelligence_confidence": 0.92,
    "openai_confidence": 0.0,
    "extracted_claim": {
        "case_number": null,
        "plaintiff_name": null,
        "defendant_name": null,
        "court_name": null,
        "is_valid": false,
        "processing_confidence": 0.5,
        "validation_errors": ["الحقل المطلوب مفقود: case_number", "الحقل المطلوب مفقود: plaintiff_name"]
    },
    "validation_score": 0.5,
    "is_valid": false,
    "validation_errors": ["الحقل المطلوب مفقود: case_number", "الحقل المطلوب مفقود: plaintiff_name"],
    "created_at": "2025-08-07T15:39:12.123456",
    "completed_at": "2025-08-07T15:39:26.234567"
}
```

**Usage:**
```bash
curl -X POST http://localhost:8000/api/v1/claim-extractor/extract \
  -F "file=@test_claim.pdf" \
  -F "conversation_id=test_conversation_123"
```

## Testing

### Run API Tests

Use the provided test script to test all endpoints:

```bash
# Start the server
python3 -m uvicorn app.main:app --reload

# In another terminal, run the tests
python3 scripts/test_claim_extractor_api.py
```

### Manual Testing with cURL

```bash
# 1. Health check
curl http://localhost:8000/api/v1/claim-extractor/health

# 2. Get sample data
curl http://localhost:8000/api/v1/claim-extractor/sample-data

# 3. Process text
curl -X POST http://localhost:8000/api/v1/claim-extractor/process-text \
  -H "Content-Type: application/json" \
  -d '{"text": "صحيفة الدعوى\nرقم الطلب: 1383951"}'

# 4. Validate claim
curl -X POST http://localhost:8000/api/v1/claim-extractor/validate \
  -H "Content-Type: application/json" \
  -d '{
    "case_number": "1383951",
    "plaintiff_name": "عبير احمد سعيد العمودي",
    "defendant_name": "أمانة منطقة الرياض"
  }'

# 5. Upload and extract from PDF
curl -X POST http://localhost:8000/api/v1/claim-extractor/extract \
  -F "file=@your_claim.pdf"
```

## Error Responses

All endpoints return consistent error responses:

```json
{
    "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `400 Bad Request`: Invalid input data
- `404 Not Found`: Endpoint not found
- `500 Internal Server Error`: Server-side error

## Configuration

Make sure these environment variables are configured:

```bash
# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_API_KEY=your-api-key-here

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-openai-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=your-storage-connection-string
AZURE_STORAGE_CONTAINER_NAME=leg-files
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Navigate to the "Claim Extractor" section to see all available endpoints with interactive testing capabilities. 