# Claim Extractor Module

This document describes the enhanced claim extraction capabilities integrated into the Maarefa Agent system. The claim extractor provides specialized functionality for extracting and processing legal claim information from PDF documents using Azure Document Intelligence and Azure OpenAI.

## Overview

The claim extractor module is designed to handle the complete pipeline of legal document processing:

1. **File Upload**: Upload PDF files to Azure Blob Storage
2. **Text Extraction**: Extract raw text using Azure Document Intelligence
3. **Structured Data Extraction**: Process and structure the extracted text
4. **AI Refinement**: Enhance results using Azure OpenAI
5. **Validation**: Validate extracted information and provide confidence scores

## Architecture

The module follows a clean, senior-level architecture with clear separation of concerns:

```
app/modules/claim_extractor/
├── __init__.py              # Module exports
├── models.py                # Data models and structures
├── service.py               # Main service orchestrator
├── text_processor.py        # Text processing and pattern matching
├── openai_refiner.py        # OpenAI integration for refinement
├── storage_manager.py       # Azure Blob Storage management
└── validator.py             # Claim validation and scoring
```

## Components

### 1. Data Models (`models.py`)

#### `ClaimInfo`
Structured representation of extracted claim information:

```python
class ClaimInfo(BaseModel):
    # Basic claim information
    case_number: Optional[str]
    claim_number: Optional[str]
    filing_date: Optional[str]
    
    # Parties information
    plaintiff_name: Optional[str]
    plaintiff_id: Optional[str]
    plaintiff_mobile: Optional[str]
    plaintiff_email: Optional[str]
    plaintiff_address: Optional[str]
    
    defendant_name: Optional[str]
    defendant_type: Optional[str]
    defendant_id: Optional[str]
    
    # Court information
    court_name: Optional[str]
    court_type: Optional[str]
    court_location: Optional[str]
    
    # Case details
    case_type: Optional[str]
    case_subject: Optional[str]
    case_facts: Optional[str]
    case_requests: Optional[str]
    
    # Additional information
    decision_number: Optional[str]
    appeal_number: Optional[str]
    violation_number: Optional[str]
    
    # Financial information
    claim_amount: Optional[str]
    currency: Optional[str] = "ريال سعودي"
    
    # Validation
    is_valid: bool = False
    validation_errors: List[str] = []
    processing_confidence: Optional[float]
```

#### `ExtractionResult`
Result of the complete extraction process:

```python
class ExtractionResult(BaseModel):
    # Processing information
    status: ProcessingStatus
    processing_id: str
    filename: str
    file_url: Optional[str]
    
    # Extraction results
    raw_text: Optional[str]
    extracted_claim: Optional[ClaimInfo]
    refined_response: Optional[str]
    
    # Processing metadata
    processing_time: Optional[float]
    document_intelligence_confidence: Optional[float]
    openai_confidence: Optional[float]
    
    # Error handling
    error_message: Optional[str]
    error_details: Optional[Dict[str, Any]]
```

### 2. Main Service (`service.py`)

The `ClaimExtractorService` orchestrates the entire extraction process:

```python
class ClaimExtractorService:
    async def extract_claim_from_pdf(
        self, 
        file_content: bytes, 
        filename: str,
        conversation_id: Optional[str] = None
    ) -> ExtractionResult:
        # 1. Upload file to blob storage
        # 2. Extract raw text using Document Intelligence
        # 3. Process and structure the text
        # 4. Refine using OpenAI
        # 5. Validate the extracted information
```

### 3. Text Processor (`text_processor.py`)

Handles structured data extraction using pattern matching:

- **Pattern-based extraction** for Arabic legal documents
- **Text cleaning and normalization**
- **Field-specific validation**
- **Section-based text analysis**

### 4. OpenAI Refiner (`openai_refiner.py`)

Enhances extracted information using Azure OpenAI:

- **Refined response generation**
- **Legal summary creation**
- **Enhanced analysis with insights**
- **Fallback mechanisms when OpenAI is unavailable**

### 5. Storage Manager (`storage_manager.py`)

Manages file operations with Azure Blob Storage:

- **File upload with unique naming**
- **Metadata retrieval**
- **File listing and management**
- **Mock storage for testing**

### 6. Validator (`validator.py`)

Validates extracted claim information:

- **Required field validation**
- **Format validation (email, phone, ID)**
- **Consistency checks**
- **Confidence scoring**

## API Integration

The claim extractor is integrated into the existing `/files/upload` endpoint:

### Enhanced Upload Endpoint

```python
@router.post("/files/upload")
async def upload_file(
    conversation_id: str = Form(...),
    user_id: str = Form(...),
    file: UploadFile = File(...),
    claim_extractor: ClaimExtractorService = Depends(get_claim_extractor_service)
):
    # Process document with enhanced claim extraction
    extracted_data = await document_processor.process_document(...)
    
    # Enhanced claim extraction using the new service
    claim_extraction_result = await claim_extractor.extract_claim_from_pdf(
        file_content=file_content,
        filename=file.filename,
        conversation_id=conversation_id
    )
    
    # Merge and return enhanced results
    enhanced_data = await _merge_extraction_results(extracted_data, claim_extraction_result)
```

### Response Format

The enhanced response includes:

```json
{
    "response": "Refined Arabic response from OpenAI",
    "file_url": "https://storage.blob.core.windows.net/...",
    "case_number": "1383951",
    "is_valid": true,
    "metadata": {
        "document_type": "صحيفة دعوى",
        "validation_score": 0.85,
        "validation_errors": [],
        "total_pages": 1,
        "processing_id": "uuid-here",
        "processing_time": 2.34,
        "document_intelligence_confidence": 0.92,
        "openai_confidence": 0.90,
        "extraction_status": "validated"
    }
}
```

## Configuration

### Environment Variables

Required environment variables:

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

## Usage Examples

### Python Usage

```python
from app.modules.claim_extractor import ClaimExtractorService

# Initialize service
extractor = ClaimExtractorService()

# Extract claim from PDF
result = await extractor.extract_claim_from_pdf(
    file_content=pdf_bytes,
    filename="claim.pdf",
    conversation_id="conversation_123"
)

# Access results
if result.extracted_claim:
    print(f"Case Number: {result.extracted_claim.case_number}")
    print(f"Plaintiff: {result.extracted_claim.plaintiff_name}")
    print(f"Court: {result.extracted_claim.court_name}")
    print(f"Valid: {result.extracted_claim.is_valid}")

print(f"Refined Response: {result.refined_response}")
```

### API Usage

```bash
# Upload file with claim extraction
curl -X POST http://localhost:8000/files/upload \
  -F "conversation_id=507f1f77bcf86cd799439011" \
  -F "user_id=user123" \
  -F "file=@claim.pdf"
```

## Testing

### Running Tests

```bash
# Run the complete test suite
python3 scripts/test_claim_extractor.py
```

### Test Coverage

The test suite covers:

- ✅ **Text Processor**: Pattern matching and data extraction
- ✅ **OpenAI Refiner**: Response generation and enhancement
- ✅ **Storage Manager**: File upload and management
- ✅ **Validator**: Field validation and scoring
- ✅ **Complete Extraction**: End-to-end pipeline testing

### Test Results

Example test output:

```
🧪 Starting Claim Extractor Test Suite
🧠 Testing Text Processor
✅ Text Processor: Extracted 8 fields
🤖 Testing OpenAI Refiner
✅ OpenAI Refiner: Refined response length: 1250
📁 Testing Storage Manager
✅ Storage Manager: Storage available: True
✅ Testing Claim Validator
✅ Claim Validator: Valid claim score: 0.85
🚀 Testing Complete Claim Extraction
✅ Complete Extraction: Status: validated, Time: 2.34s

📊 Test Summary:
   Total Tests: 5
   Passed: 5
   Failed: 0
   Success Rate: 100.0%
   Execution Time: 3.45s
   Overall Status: ALL_PASSED
```

## Error Handling

The module includes comprehensive error handling:

### Graceful Degradation

- **OpenAI unavailable**: Falls back to basic response generation
- **Storage unavailable**: Uses mock URLs for testing
- **Document Intelligence errors**: Continues with available data

### Error Types

```python
# Processing errors
ProcessingStatus.FAILED: "Processing failed due to error"
ProcessingStatus.INVALID: "Document validation failed"

# Field validation errors
"الحقل المطلوب مفقود: case_number"
"رقم الجوال غير صحيح"
"البريد الإلكتروني غير صحيح"
```

## Performance Considerations

### Processing Time

- **Document Intelligence**: ~1-3 seconds per document
- **OpenAI Refinement**: ~1-2 seconds per document
- **Total Processing**: ~2-5 seconds per document

### Optimization

- **Parallel processing** of multiple models
- **Caching** of common patterns
- **Async operations** for I/O-bound tasks
- **Connection pooling** for Azure services

## Security

### Data Protection

- **Secure file upload** to Azure Blob Storage
- **Encrypted connections** to Azure services
- **No sensitive data logging**
- **Temporary file cleanup**

### Access Control

- **Conversation-based file organization**
- **User authentication** required
- **File access validation**

## Monitoring and Logging

### Log Levels

```python
# Info level for successful operations
logger.info(f"Claim extraction completed for {filename} in {processing_time:.2f}s")

# Warning level for non-critical issues
logger.warning("OpenAI client not available, returning basic response")

# Error level for failures
logger.error(f"Error extracting claim from {filename}: {e}")
```

### Metrics

Trackable metrics include:

- Processing time per document
- Success/failure rates
- Confidence scores
- Field extraction accuracy
- API response times

## Future Enhancements

### Planned Features

1. **Multi-language Support**: Support for English legal documents
2. **Batch Processing**: Process multiple documents simultaneously
3. **Custom Models**: Train custom Document Intelligence models
4. **Advanced Validation**: Legal compliance checking
5. **Integration APIs**: Connect with external legal systems

### Scalability Improvements

1. **Queue-based Processing**: Handle high-volume document processing
2. **Distributed Processing**: Scale across multiple instances
3. **Caching Layer**: Redis-based caching for repeated patterns
4. **Database Optimization**: Efficient storage and retrieval

## Troubleshooting

### Common Issues

1. **OpenAI Connection Errors**
   - Check API key and endpoint configuration
   - Verify deployment name
   - Check network connectivity

2. **Document Intelligence Errors**
   - Validate document format (PDF, JPEG, PNG)
   - Check file size limits
   - Verify API credentials

3. **Storage Errors**
   - Check connection string
   - Verify container permissions
   - Ensure container exists

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("app.modules.claim_extractor").setLevel(logging.DEBUG)
```

## Support

For issues and questions:

1. Check the test logs for detailed error information
2. Verify environment variable configuration
3. Test individual components using the test script
4. Review Azure service quotas and limits

---

This enhanced claim extractor module provides a robust, scalable solution for legal document processing with comprehensive error handling, validation, and AI-powered refinement capabilities. 