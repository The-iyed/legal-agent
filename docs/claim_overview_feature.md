# Claim Overview Feature

## Overview

The Claim Overview feature provides users with clear, user-friendly explanations of legal claims extracted from documents. This feature automatically generates comprehensive summaries that help users understand the key aspects of their legal cases without needing to interpret complex legal documents.

## Features

### 1. Automatic Claim Overview Generation

The system automatically generates claim overviews during the document processing pipeline:

- **Text Processing**: Extracts basic claim overview information using pattern matching
- **AI Enhancement**: Uses Azure OpenAI to generate comprehensive, user-friendly summaries
- **Fallback Mechanism**: Provides basic overviews when AI services are unavailable

### 2. Concise Overview Format

Claim overviews are generated in a concise, chatbot-friendly format:

```
دعوى [نوع الدعوى] مقدمة من [اسم المدعي] ضد [اسم المدعى عليه]، [السبب الرئيسي] بمبلغ [المبلغ] [العملة].
```

**Example:**
```
دعوى إدارية مقدمة من عبير احمد سعيد العمودي ضد أمانة منطقة الرياض، تطلب إلغاء قرار إداري والتعويض عن الأضرار بمبلغ 50000 ريال سعودي.
```

### 3. Multiple Generation Methods

The system supports multiple ways to generate claim overviews:

- **Automatic**: Generated during full document extraction
- **On-demand**: Via dedicated API endpoint
- **Text-only**: From raw text without structured data
- **Enhanced**: With structured claim data for better accuracy

## API Endpoints

### 1. Full Document Extraction with Overview

**Endpoint**: `POST /api/v1/claim-extractor/extract`

**Description**: Extracts complete claim information including automatically generated overview

**Response**:
```json
{
  "status": "success",
  "extracted_claim": {
    "case_number": "1383951",
    "plaintiff_name": "عبير احمد سعيد العمودي",
    "defendant_name": "أمانة منطقة الرياض",
    "claim_overview": "دعوى إدارية مقدمة من عبير احمد سعيد العمودي ضد أمانة منطقة الرياض، تطلب إلغاء قرار إداري والتعويض عن الأضرار بمبلغ 50000 ريال سعودي.",
    // ... other fields
  }
}
```

### 2. Dedicated Overview Generation

**Endpoint**: `POST /api/v1/claim-extractor/generate-overview`

**Description**: Generates claim overview from text and optional structured data

**Request**:
```json
{
  "raw_text": "صحيفة الدعوى...",
  "extracted_claim": {
    "case_number": "1383951",
    "plaintiff_name": "عبير احمد سعيد العمودي"
    // ... optional structured data
  }
}
```

**Response**:
```json
{
  "status": "success",
  "claim_overview": "دعوى إدارية مقدمة من عبير احمد سعيد العمودي ضد أمانة منطقة الرياض، تطلب إلغاء قرار إداري والتعويض عن الأضرار بمبلغ 50000 ريال سعودي.",
  "claim_overview_length": 116,
  "has_claim_data": true,
  "openai_available": true,
  "generated_at": "2024-01-15T10:30:00Z"
}
```

### 3. Enhanced Refinement with Overview

**Endpoint**: `POST /api/v1/claim-extractor/refine`

**Description**: Refines extraction and generates overview

**Response**:
```json
{
  "status": "success",
  "refined_response": "...",
  "claim_overview": "دعوى إدارية مقدمة من عبير احمد سعيد العمودي ضد أمانة منطقة الرياض، تطلب إلغاء قرار إداري والتعويض عن الأضرار بمبلغ 50000 ريال سعودي.",
  "claim_overview_length": 116,
  "legal_summary": "...",
  "enhanced_analysis": {...}
}
```

### 4. Sample Data with Overview

**Endpoint**: `GET /api/v1/claim-extractor/sample-data`

**Description**: Returns sample data including claim overview examples

**Response**:
```json
{
  "sample_claim": {
    "case_number": "1383951",
    "claim_overview": "دعوى إدارية مقدمة من عبير احمد سعيد العمودي ضد أمانة منطقة الرياض، تطلب إلغاء قرار إداري والتعويض عن الأضرار بمبلغ 50000 ريال سعودي."
  },
  "sample_overview": "دعوى إدارية مقدمة من عبير احمد سعيد العمودي ضد أمانة منطقة الرياض، تطلب إلغاء قرار إداري والتعويض عن الأضرار بمبلغ 50000 ريال سعودي.",
  "usage_examples": {
    "generate_overview": "POST /api/v1/claim-extractor/generate-overview with sample_text and sample_claim"
  }
}
```

## Implementation Details

### 1. Data Model

The `ClaimInfo` model includes the claim overview field:

```python
class ClaimInfo(BaseModel):
    # ... other fields
    claim_overview: Optional[str] = Field(
        None, 
        description="ملخص الدعوى - شرح مبسط للمستخدم"
    )
```

### 2. Text Processing

Enhanced pattern matching for claim overview extraction:

```python
"claim_overview": [
    r"موضوع\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
    r"الموضوع\s*[:\-]?\s*([^\n\r]+)",
    r"سبب\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
    r"وصف\s*الطلب\s*[:\-]?\s*([^\n\r]+)",
    r"ملخص\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
    r"شرح\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
    r"تفاصيل\s*الدعوى\s*[:\-]?\s*([^\n\r]+)",
    # ... more patterns
]
```

### 3. OpenAI Integration

The `OpenAIRefiner` class provides claim overview generation:

```python
async def generate_claim_overview(
    self, 
    raw_text: str, 
    extracted_claim: Optional[ClaimInfo] = None
) -> str:
    """Generate a user-friendly claim overview explaining the case."""
```

### 4. Service Integration

The `ClaimExtractorService` automatically generates overviews during refinement:

```python
async def _refine_with_openai(self, result: ExtractionResult) -> ExtractionResult:
    # ... existing refinement logic
    
    # Generate claim overview for user-friendly explanation
    if result.extracted_claim:
        claim_overview = await self.openai_refiner.generate_claim_overview(
            raw_text=result.raw_text,
            extracted_claim=result.extracted_claim
        )
        result.extracted_claim.claim_overview = claim_overview
```

## Usage Examples

### 1. Basic Usage

```python
from app.modules.claim_extractor import ClaimExtractorService

service = ClaimExtractorService()

# Extract claim with automatic overview generation
result = await service.extract_claim_from_pdf(
    file_content=pdf_content,
    filename="claim.pdf"
)

# Access the generated overview
overview = result.extracted_claim.claim_overview
print(overview)
```

### 2. Standalone Overview Generation

```python
from app.modules.claim_extractor.openai_refiner import OpenAIRefiner

refiner = OpenAIRefiner()

# Generate overview from text only
overview = await refiner.generate_claim_overview(
    raw_text="صحيفة الدعوى...",
    extracted_claim=None
)

# Generate overview with structured data
overview = await refiner.generate_claim_overview(
    raw_text="صحيفة الدعوى...",
    extracted_claim=claim_info
)
```

### 3. API Usage

```bash
# Generate overview via API
curl -X POST "http://localhost:8000/api/v1/claim-extractor/generate-overview" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "صحيفة الدعوى...",
    "extracted_claim": {
      "case_number": "1383951",
      "plaintiff_name": "عبير احمد سعيد العمودي"
    }
  }'
```

## Benefits

### 1. User Experience
- **Clear Understanding**: Users get plain-language explanations of complex legal documents
- **Concise Format**: Information is presented in a single, easy-to-read sentence
- **Chatbot-Friendly**: Perfect length and format for conversational interfaces
- **Arabic Language**: All overviews are generated in Arabic for local users

### 2. Accessibility
- **No Legal Expertise Required**: Users don't need legal knowledge to understand their cases
- **Consistent Format**: All overviews follow the same concise format
- **Essential Information**: Covers the most important aspects of the case in one sentence

### 3. Technical Benefits
- **Automatic Generation**: No manual intervention required
- **Fallback Support**: Works even when AI services are unavailable
- **Integration Ready**: Seamlessly integrated into existing workflows

## Testing

The feature includes comprehensive testing:

```bash
# Run the test script
python3 scripts/test_claim_overview.py
```

The test script verifies:
- OpenAI integration
- Service integration
- API endpoints
- Fallback mechanisms
- Content validation

## Configuration

### Environment Variables

The feature uses existing OpenAI configuration:

```bash
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
```

### Fallback Behavior

When OpenAI is unavailable, the system provides basic overviews using extracted structured data, ensuring the feature always works.

## Future Enhancements

Potential improvements for the claim overview feature:

1. **Multi-language Support**: Generate overviews in multiple languages
2. **Customizable Templates**: Allow users to customize overview formats
3. **Interactive Overviews**: Add clickable elements for more details
4. **Export Options**: Support for PDF, Word, or other formats
5. **Version History**: Track changes to overviews over time
6. **User Feedback**: Allow users to rate and improve overviews

## Conclusion

The Claim Overview feature significantly enhances the user experience by providing clear, understandable explanations of legal claims. It bridges the gap between complex legal documents and user comprehension, making the system more accessible and user-friendly. 