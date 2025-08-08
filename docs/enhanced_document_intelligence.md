# Enhanced Document Intelligence

This document describes the enhanced document intelligence capabilities integrated into the Maarefa Agent system using Azure Document Intelligence.

## Overview

The enhanced document intelligence system provides comprehensive document analysis capabilities using Azure Document Intelligence with multiple analysis models and specialized features for legal document processing.

## Features

### 1. Multiple Analysis Models

The system supports various Azure Document Intelligence models:

- **Layout Analysis** (`prebuilt-layout`): Extract text, tables, and layout information
- **Document Analysis** (`prebuilt-document`): Extract text, key-value pairs, and form fields
- **Read** (`prebuilt-read`): High-accuracy text extraction with OCR
- **Invoice Analysis** (`prebuilt-invoice`): Structured data extraction from invoices
- **Receipt Analysis** (`prebuilt-receipt`): Receipt processing and expense tracking
- **ID Document Analysis** (`prebuilt-idDocument`): Identity document processing
- **Business Card Analysis** (`prebuilt-businessCard`): Contact information extraction
- **W2 Form Analysis** (`prebuilt-w2`): Tax form processing

### 2. Legal Document Processing

Specialized capabilities for Saudi legal documents:

- **Field Extraction**: Automatic extraction of legal document fields
- **Pattern Recognition**: Arabic text pattern matching for legal terms
- **Multi-model Analysis**: Combined analysis using multiple models for better accuracy
- **Validation**: Document validation and confidence scoring

### 3. Document Summarization

Comprehensive document analysis summaries including:

- Document type classification
- Content statistics
- Structure analysis
- Processing metrics

## API Endpoints

### Base URL
```
/api/v1/document-intelligence
```

### 1. Analyze Document
**POST** `/analyze`

Analyze a document using a specific model.

**Parameters:**
- `file`: Document file (multipart/form-data)
- `model`: Analysis model to use (default: "prebuilt-document")
- `features`: Optional features to enable

**Response:**
```json
{
  "filename": "document.pdf",
  "model_used": "prebuilt-document",
  "confidence": 0.95,
  "pages": 2,
  "processing_time": 1.23,
  "languages": ["ar", "en"],
  "extracted_text": "...",
  "key_value_pairs": {...},
  "form_fields": {...},
  "tables_count": 1,
  "images_count": 0,
  "paragraphs_count": 15,
  "lines_count": 45,
  "words_count": 234,
  "analysis_timestamp": "2024-01-01T12:00:00Z"
}
```

### 2. Analyze with Multiple Models
**POST** `/analyze-multiple`

Analyze a document using multiple models simultaneously.

**Parameters:**
- `file`: Document file (multipart/form-data)
- `models`: List of models to use (optional)

**Response:**
```json
{
  "filename": "document.pdf",
  "models_used": ["prebuilt-document", "prebuilt-layout", "prebuilt-read"],
  "results": {
    "prebuilt-document": {
      "confidence": 0.95,
      "pages": 2,
      "processing_time": 1.23,
      "languages": ["ar"],
      "extracted_text_length": 1234,
      "key_value_pairs_count": 5,
      "form_fields_count": 3,
      "tables_count": 1,
      "images_count": 0
    }
  },
  "analysis_timestamp": "2024-01-01T12:00:00Z"
}
```

### 3. Extract Legal Fields
**POST** `/extract-legal-fields`

Extract legal document fields using specialized analysis.

**Parameters:**
- `file`: Legal document file (multipart/form-data)

**Response:**
```json
{
  "filename": "legal_document.pdf",
  "document_type": "legal_document",
  "confidence": 0.92,
  "pages": 1,
  "processing_time": 2.45,
  "extracted_fields": {
    "case_number": "١٣٨٣٩٥١",
    "plaintiff": "عبير احمد سعيد العمودي",
    "defendant": "أمانة منطقة الرياض",
    "court": "المحكمة الإدارية بالرياض",
    "case_type": "دعوى إدارية",
    "filing_date": "١٤٤٤/٠٣/١٩",
    "case_subject": "طلب إلغاء قرار إداري",
    "request": "إلغاء القرار الإداري والتعويض",
    "mobile": "٠٥٤٨٠٠٦٧٠٠",
    "email": "maabeer@gmail.com"
  },
  "raw_text": "...",
  "key_value_pairs": {...},
  "form_fields": {...},
  "extraction_timestamp": "2024-01-01T12:00:00Z"
}
```

### 4. Document Summary
**POST** `/summary`

Get a comprehensive summary of document analysis.

**Parameters:**
- `file`: Document file (multipart/form-data)

**Response:**
```json
{
  "filename": "document.pdf",
  "document_type": "form_document",
  "confidence": 0.95,
  "pages": 2,
  "languages": ["ar", "en"],
  "has_tables": true,
  "has_images": false,
  "key_value_pairs_count": 8,
  "form_fields_count": 5,
  "text_length": 1234,
  "processing_time": 1.23,
  "extracted_text_preview": "...",
  "summary_timestamp": "2024-01-01T12:00:00Z"
}
```

### 5. Available Models
**GET** `/models`

Get list of available document analysis models.

**Response:**
```json
{
  "available_models": {
    "prebuilt-layout": {
      "name": "Layout Analysis",
      "description": "Extract text, tables, and layout information from documents",
      "best_for": ["General document analysis", "Layout extraction", "Table detection"]
    },
    "prebuilt-document": {
      "name": "Document Analysis",
      "description": "Extract text, key-value pairs, and form fields from documents",
      "best_for": ["Form processing", "Key-value extraction", "General document analysis"]
    }
  },
  "total_models": 8,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 6. Health Check
**GET** `/health`

Check the health of the Document Intelligence service.

**Response:**
```json
{
  "service": "Document Intelligence",
  "status": "healthy",
  "client_initialized": true,
  "endpoint_configured": true,
  "api_key_configured": true,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Configuration

### Environment Variables

Required environment variables for Azure Document Intelligence:

```bash
# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_API_KEY=your-api-key-here

# Azure Storage (for file handling)
AZURE_STORAGE_CONNECTION_STRING=your-storage-connection-string
AZURE_STORAGE_CONTAINER_NAME=leg-files
```

### Service Configuration

The enhanced document intelligence service is automatically initialized when the application starts. It checks for required environment variables and initializes the Azure Document Intelligence client.

## Usage Examples

### Python Client Example

```python
import requests

# Analyze document with specific model
with open('document.pdf', 'rb') as f:
    files = {'file': f}
    data = {'model': 'prebuilt-document'}
    response = requests.post(
        'http://localhost:8000/api/v1/document-intelligence/analyze',
        files=files,
        data=data
    )
    result = response.json()
    print(f"Extracted text: {result['extracted_text'][:200]}...")

# Extract legal fields
with open('legal_document.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:8000/api/v1/document-intelligence/extract-legal-fields',
        files=files
    )
    result = response.json()
    print(f"Case number: {result['extracted_fields']['case_number']}")
```

### cURL Examples

```bash
# Analyze document
curl -X POST "http://localhost:8000/api/v1/document-intelligence/analyze" \
  -F "file=@document.pdf" \
  -F "model=prebuilt-document"

# Extract legal fields
curl -X POST "http://localhost:8000/api/v1/document-intelligence/extract-legal-fields" \
  -F "file=@legal_document.pdf"

# Get available models
curl -X GET "http://localhost:8000/api/v1/document-intelligence/models"

# Health check
curl -X GET "http://localhost:8000/api/v1/document-intelligence/health"
```

## Testing

### Test Scripts

Two test scripts are available for validating the document intelligence capabilities:

1. **Basic Azure Services Test** (`scripts/test_azure_services.py`)
   - Tests basic Azure service connectivity
   - Validates environment variables
   - Checks service health

2. **Enhanced Document Intelligence Test** (`scripts/test_document_intelligence.py`)
   - Tests all enhanced features
   - Validates multiple model analysis
   - Tests legal document extraction
   - Checks document summarization

### Running Tests

```bash
# Basic Azure services test
python scripts/test_azure_services.py

# Enhanced document intelligence test
python scripts/test_document_intelligence.py
```

## Error Handling

### Common Error Responses

**400 Bad Request**
```json
{
  "detail": "No file provided"
}
```

**400 Bad Request - Invalid Model**
```json
{
  "detail": "Invalid model. Available models: ['prebuilt-layout', 'prebuilt-document', ...]"
}
```

**500 Internal Server Error**
```json
{
  "detail": "Document analysis failed: Azure Document Intelligence client not initialized"
}
```

### Error Recovery

1. **Service Not Initialized**: Check environment variables and Azure service status
2. **Invalid Model**: Use one of the available models from `/models` endpoint
3. **File Processing Error**: Ensure file is valid and supported format
4. **Network Issues**: Check connectivity to Azure services

## Performance Considerations

### Processing Times

- **Small documents (< 1MB)**: 1-3 seconds
- **Medium documents (1-5MB)**: 3-10 seconds
- **Large documents (> 5MB)**: 10+ seconds

### Optimization Tips

1. **Use appropriate models**: Choose the right model for your document type
2. **Batch processing**: Use multiple models only when necessary
3. **File size**: Optimize document size for faster processing
4. **Caching**: Results are cached to avoid reprocessing

## Security

### Data Privacy

- Documents are processed in Azure's secure environment
- No document content is stored permanently
- Processing results are temporary and not logged
- API keys are encrypted and secure

### Access Control

- API endpoints require proper authentication
- Rate limiting is implemented
- File size limits are enforced
- Supported file types are validated

## Troubleshooting

### Common Issues

1. **Service Not Available**
   - Check Azure Document Intelligence service status
   - Verify endpoint and API key
   - Ensure proper network connectivity

2. **Poor Extraction Quality**
   - Try different analysis models
   - Check document quality and format
   - Use multiple model analysis for better results

3. **Slow Processing**
   - Optimize document size
   - Use appropriate model for document type
   - Check Azure service performance

### Debug Information

Enable debug logging to get detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Support

For issues with the enhanced document intelligence features:

1. Check the health endpoint: `/api/v1/document-intelligence/health`
2. Run the test scripts to validate functionality
3. Review logs for detailed error information
4. Verify Azure service configuration

## Future Enhancements

Planned improvements for the document intelligence system:

1. **Custom Model Training**: Support for custom document models
2. **Batch Processing**: Process multiple documents simultaneously
3. **Advanced Analytics**: Document comparison and similarity analysis
4. **Real-time Processing**: Stream processing for large document sets
5. **Enhanced Legal Processing**: More specialized legal document features
6. **Multi-language Support**: Better support for various languages
7. **Document Classification**: Automatic document type detection
8. **Content Extraction**: Advanced content structure analysis 