# Enhanced PDF Processing with Page Splitting

This document describes the enhanced PDF processing capabilities that split PDFs into individual pages and use Azure Document Intelligence to ensure comprehensive text and information extraction.

## Overview

The enhanced PDF processing system provides:

- **PDF Splitting**: Automatic splitting of multi-page PDFs into individual pages
- **Page-by-Page Analysis**: Each page is processed individually with Document Intelligence
- **Multi-Model Extraction**: Uses multiple Document Intelligence models for better coverage
- **Comprehensive Text Extraction**: Ensures all text and information is captured
- **Fallback Mechanisms**: PyPDF2 fallback when Document Intelligence is unavailable

## Architecture

### Components

1. **PDFSplitterService**: Core service for splitting PDFs and processing pages
2. **DocumentProcessorService**: Enhanced with PDF splitting capabilities
3. **ClaimExtractorService**: Updated to use enhanced PDF processing
4. **API Endpoints**: New endpoints for enhanced PDF processing

### Processing Flow

```
PDF Upload → Split into Pages → Process Each Page → Combine Results → Return Enhanced Text
     ↓              ↓                ↓                ↓              ↓
  Validate    PyPDF2 Split    Document Intelligence   Merge Text   Structured Data
```

## Features

### 1. PDF Splitting

The system automatically splits multi-page PDFs into individual pages using PyPDF2:

```python
# Split PDF into pages
pages = await pdf_splitter._split_pdf_into_pages(file_content, filename)

# Each page is processed individually
for page_num, page_content in enumerate(pages, 1):
    page_result = await pdf_splitter._extract_text_from_page(
        page_content, filename, page_num
    )
```

### 2. Page-by-Page Document Intelligence

Each page is processed with Azure Document Intelligence for optimal text extraction:

- **Layout Analysis**: Better structure recognition
- **Paragraph Detection**: Maintains document structure
- **Line Grouping**: Groups lines by vertical position
- **Key-Value Extraction**: Identifies form fields and structured data

### 3. Multi-Model Extraction

The system tries multiple Document Intelligence models for each page:

- `prebuilt-layout`: Best for structured documents
- `prebuilt-document`: Best for forms and key-value pairs
- `prebuilt-read`: Best for text extraction and OCR

The system selects the best result based on:
- Text length extracted
- Confidence score
- Model performance

### 4. Fallback Mechanisms

If Document Intelligence fails, the system falls back to PyPDF2:

```python
# Try Document Intelligence first
try:
    result = await document_intelligence.analyze_document(page_content)
    extracted_text = result.extracted_text
except Exception:
    # Fallback to PyPDF2
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(page_content))
    extracted_text = pdf_reader.pages[0].extract_text()
```

## API Endpoints

### 1. Enhanced PDF Analysis

**Endpoint**: `POST /api/v1/document-intelligence/analyze-pdf-enhanced`

**Description**: Analyze PDF with page-by-page processing

**Parameters**:
- `file`: PDF file (multipart/form-data)
- `extract_per_page`: Whether to extract text from each page individually (default: true)
- `combine_results`: Whether to combine results from all pages (default: true)

**Response**:
```json
{
  "success": true,
  "filename": "document.pdf",
  "total_pages": 3,
  "extracted_text": "Combined text from all pages...",
  "page_results": [
    {
      "page_number": 1,
      "extracted_text": "Page 1 text...",
      "confidence": 0.95,
      "key_value_pairs": {},
      "form_fields": {},
      "processing_time": 1.2,
      "success": true
    }
  ],
  "processing_timestamp": "2024-01-01T12:00:00Z",
  "processing_id": "uuid-123",
  "extraction_method": "page_by_page"
}
```

### 2. Multi-Model PDF Analysis

**Endpoint**: `POST /api/v1/document-intelligence/analyze-pdf-multi-model`

**Description**: Analyze PDF using multiple Document Intelligence models

**Parameters**:
- `file`: PDF file (multipart/form-data)

**Response**:
```json
{
  "success": true,
  "filename": "document.pdf",
  "total_pages": 3,
  "extracted_text": "Combined text from best models...",
  "page_results": [
    {
      "page_number": 1,
      "extracted_text": "Page 1 text...",
      "confidence": 0.98,
      "model_used": "prebuilt-layout",
      "success": true
    }
  ],
  "processing_timestamp": "2024-01-01T12:00:00Z",
  "processing_id": "uuid-123",
  "extraction_method": "multi_model"
}
```

### 3. Available Models

**Endpoint**: `GET /api/v1/document-intelligence/models`

**Description**: Get list of available Document Intelligence models

**Response**:
```json
{
  "success": true,
  "models": [
    {
      "value": "prebuilt-layout",
      "name": "LAYOUT",
      "description": "Azure Document Intelligence LAYOUT model"
    }
  ],
  "count": 1
}
```

### 4. Text Extraction Only

**Endpoint**: `POST /api/v1/document-intelligence/extract-text-only`

**Description**: Extract only text content from document

**Parameters**:
- `file`: Document file (multipart/form-data)

**Response**:
```json
{
  "success": true,
  "filename": "document.pdf",
  "extracted_text": "Extracted text content...",
  "confidence": 0.95,
  "pages": 3,
  "processing_time": 2.1
}
```

## Integration with Existing Services

### Document Processor Service

The `DocumentProcessorService` has been enhanced to automatically use PDF splitting for PDF files:

```python
async def _extract_raw_text_only(self, file_content: bytes, filename: str) -> str:
    # Check if this is a PDF file
    if filename.lower().endswith('.pdf'):
        return await self._extract_pdf_with_page_splitting(file_content, filename)
    
    # Use original method for non-PDF files
    # ...
```

### Claim Extractor Service

The `ClaimExtractorService` now uses enhanced PDF processing:

```python
async def _extract_raw_text(self, result: ExtractionResult, file_content: bytes) -> ExtractionResult:
    # Check if this is a PDF file for enhanced processing
    if result.filename.lower().endswith('.pdf'):
        # Use enhanced PDF extraction with page splitting
        extracted_text = await doc_processor._extract_pdf_with_page_splitting(
            file_content, result.filename
        )
        # ...
```

## Configuration

### Environment Variables

Ensure the following environment variables are set:

```bash
# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_API_KEY=your-api-key

# Azure Storage (for file uploads)
AZURE_STORAGE_CONNECTION_STRING=your-storage-connection-string
```

### Dependencies

The enhanced PDF processing requires:

```txt
PyPDF2>=3.0.0
azure-ai-formrecognizer>=3.3.3
```

## Usage Examples

### 1. Basic PDF Processing

```python
from app.modules.document_processor.pdf_splitter import PDFSplitterService

# Initialize service
pdf_splitter = PDFSplitterService()

# Process PDF
result = await pdf_splitter.split_and_extract_pdf(
    file_content=pdf_bytes,
    filename="document.pdf"
)

if result["success"]:
    print(f"Extracted {len(result['extracted_text'])} characters")
    print(f"Processed {result['total_pages']} pages")
```

### 2. Multi-Model Processing

```python
# Use multiple models for better coverage
result = await pdf_splitter.extract_with_multiple_models(
    file_content=pdf_bytes,
    filename="document.pdf"
)

# Check which models were used
for page_result in result["page_results"]:
    print(f"Page {page_result['page_number']}: {page_result['model_used']}")
```

### 3. Integration with Document Processor

```python
from app.modules.document_processor.service import DocumentProcessorService

# Initialize service
doc_processor = DocumentProcessorService()

# Process document (automatically uses PDF splitting for PDFs)
extracted_text = await doc_processor._extract_raw_text_only(
    file_content=file_bytes,
    filename="document.pdf"
)
```

## Testing

### Test Script

Run the test script to verify the enhanced PDF processing:

```bash
python scripts/test_enhanced_pdf_processing.py
```

### Manual Testing

1. Start the server:
```bash
uvicorn app.main:app --reload
```

2. Test the API endpoints:
```bash
# Enhanced PDF analysis
curl -X POST "http://localhost:8000/api/v1/document-intelligence/analyze-pdf-enhanced" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-document.pdf"

# Multi-model analysis
curl -X POST "http://localhost:8000/api/v1/document-intelligence/analyze-pdf-multi-model" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-document.pdf"
```

## Performance Considerations

### Processing Time

- **Single page**: ~1-2 seconds
- **Multi-page PDF**: ~1-2 seconds per page
- **Large documents**: Consider async processing for documents >10 pages

### Memory Usage

- Each page is processed individually to minimize memory usage
- Page content is released after processing
- Large PDFs are handled efficiently

### Error Handling

- Individual page failures don't stop processing of other pages
- Fallback mechanisms ensure text extraction even if Document Intelligence fails
- Comprehensive error logging for debugging

## Best Practices

### 1. File Size Limits

- Recommended maximum: 50MB per PDF
- For larger files, consider splitting before upload
- Monitor processing time for very large documents

### 2. Model Selection

- Use `analyze-pdf-enhanced` for general processing
- Use `analyze-pdf-multi-model` for maximum accuracy
- Use `extract-text-only` for simple text extraction

### 3. Error Handling

- Always check the `success` field in responses
- Handle individual page failures gracefully
- Log processing statistics for monitoring

### 4. Caching

- Consider caching results for frequently processed documents
- Use processing IDs for result tracking
- Implement retry logic for transient failures

## Troubleshooting

### Common Issues

1. **Document Intelligence not available**
   - Check environment variables
   - Verify Azure service is running
   - System will fallback to PyPDF2

2. **PDF splitting fails**
   - Check if PDF is corrupted
   - Verify PyPDF2 is installed
   - Try with a different PDF

3. **Low confidence scores**
   - Try multi-model processing
   - Check document quality
   - Verify Document Intelligence credentials

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger('app.modules.document_processor.pdf_splitter').setLevel(logging.DEBUG)
```

Check processing logs for detailed information about each step.

## Future Enhancements

### Planned Features

1. **Parallel Processing**: Process multiple pages simultaneously
2. **Custom Models**: Support for custom Document Intelligence models
3. **Batch Processing**: Handle multiple PDFs in a single request
4. **Progress Tracking**: Real-time progress updates for large documents
5. **Advanced Caching**: Intelligent caching based on document content

### Performance Optimizations

1. **Streaming Processing**: Process pages as they're split
2. **Memory Optimization**: Reduce memory footprint for large documents
3. **Connection Pooling**: Optimize Document Intelligence connections
4. **Result Compression**: Compress large extraction results

## Conclusion

The enhanced PDF processing system provides comprehensive text extraction capabilities by combining PDF splitting with Azure Document Intelligence. This ensures that all text and information is captured from multi-page documents, making it ideal for legal document processing and other applications requiring high-accuracy text extraction.

The system is designed to be robust, with multiple fallback mechanisms and comprehensive error handling, ensuring reliable operation even when external services are unavailable. 