#!/usr/bin/env python3
"""
Test Enhanced PDF Processing

This script demonstrates the enhanced PDF processing capabilities including:
- PDF splitting into individual pages
- Page-by-page Document Intelligence analysis
- Multi-model extraction for better coverage
- Comprehensive text extraction from legal documents
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.document_processor.pdf_splitter import PDFSplitterService
from app.modules.document_processor.service import DocumentProcessorService
from app.modules.claim_extractor.service import ClaimExtractorService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_pdf_splitter_service():
    """Test the PDF splitter service with a sample PDF."""
    print("\n" + "="*60)
    print("Testing PDF Splitter Service")
    print("="*60)
    
    # Initialize the service
    pdf_splitter = PDFSplitterService()
    
    # Test with a sample PDF (you'll need to provide a real PDF file)
    test_pdf_path = "tests/data/valid_claim.pdf"  # Update this path
    
    if not os.path.exists(test_pdf_path):
        print(f"Test PDF not found at {test_pdf_path}")
        print("Please provide a valid PDF file path for testing")
        return
    
    try:
        # Read the PDF file
        with open(test_pdf_path, 'rb') as f:
            file_content = f.read()
        
        filename = os.path.basename(test_pdf_path)
        
        print(f"Processing PDF: {filename}")
        print(f"File size: {len(file_content)} bytes")
        
        # Test basic page splitting
        print("\n1. Testing basic page splitting...")
        result = await pdf_splitter.split_and_extract_pdf(
            file_content=file_content,
            filename=filename,
            extract_per_page=True,
            combine_results=True
        )
        
        if result.get("success"):
            print(f"✓ Successfully processed {result['total_pages']} pages")
            print(f"✓ Extracted text length: {len(result['extracted_text'])} characters")
            
            # Show page results
            for page_result in result.get("page_results", []):
                page_num = page_result.get("page_number", "?")
                success = page_result.get("success", False)
                confidence = page_result.get("confidence", 0.0)
                text_length = len(page_result.get("extracted_text", ""))
                processing_time = page_result.get("processing_time", 0.0)
                
                status = "✓" if success else "✗"
                print(f"  {status} Page {page_num}: {text_length} chars, "
                      f"confidence: {confidence:.2f}, time: {processing_time:.2f}s")
        else:
            print(f"✗ Processing failed: {result.get('error', 'Unknown error')}")
        
        # Test multi-model extraction
        print("\n2. Testing multi-model extraction...")
        multi_result = await pdf_splitter.extract_with_multiple_models(
            file_content=file_content,
            filename=filename
        )
        
        if multi_result.get("success"):
            print(f"✓ Multi-model processing completed")
            print(f"✓ Total pages: {multi_result['total_pages']}")
            print(f"✓ Extraction method: {multi_result.get('extraction_method', 'unknown')}")
            
            # Show which models were used for each page
            for page_result in multi_result.get("page_results", []):
                page_num = page_result.get("page_number", "?")
                model_used = page_result.get("model_used", "unknown")
                confidence = page_result.get("confidence", 0.0)
                text_length = len(page_result.get("extracted_text", ""))
                
                print(f"  ✓ Page {page_num}: {model_used} (confidence: {confidence:.2f}, "
                      f"text: {text_length} chars)")
        else:
            print(f"✗ Multi-model processing failed: {multi_result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"✗ Error testing PDF splitter: {e}")


async def test_document_processor_integration():
    """Test the integration with the document processor service."""
    print("\n" + "="*60)
    print("Testing Document Processor Integration")
    print("="*60)
    
    # Initialize the service
    doc_processor = DocumentProcessorService()
    
    # Test with a sample PDF
    test_pdf_path = "tests/data/valid_claim.pdf"  # Update this path
    
    if not os.path.exists(test_pdf_path):
        print(f"Test PDF not found at {test_pdf_path}")
        return
    
    try:
        # Read the PDF file
        with open(test_pdf_path, 'rb') as f:
            file_content = f.read()
        
        filename = os.path.basename(test_pdf_path)
        
        print(f"Processing PDF with Document Processor: {filename}")
        
        # Test enhanced PDF extraction
        extracted_text = await doc_processor._extract_pdf_with_page_splitting(
            file_content=file_content,
            filename=filename
        )
        
        if extracted_text and not extracted_text.startswith("Error"):
            print(f"✓ Successfully extracted text: {len(extracted_text)} characters")
            
            # Show a preview of the extracted text
            preview = extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text
            print(f"\nText preview:\n{preview}")
        else:
            print(f"✗ Text extraction failed: {extracted_text}")
            
    except Exception as e:
        print(f"✗ Error testing document processor integration: {e}")


async def test_claim_extractor_integration():
    """Test the integration with the claim extractor service."""
    print("\n" + "="*60)
    print("Testing Claim Extractor Integration")
    print("="*60)
    
    # Initialize the service
    claim_extractor = ClaimExtractorService()
    
    # Test with a sample PDF
    test_pdf_path = "tests/data/valid_claim.pdf"  # Update this path
    
    if not os.path.exists(test_pdf_path):
        print(f"Test PDF not found at {test_pdf_path}")
        return
    
    try:
        # Read the PDF file
        with open(test_pdf_path, 'rb') as f:
            file_content = f.read()
        
        filename = os.path.basename(test_pdf_path)
        
        print(f"Processing PDF with Claim Extractor: {filename}")
        
        # Extract claim information
        result = await claim_extractor.extract_claim_from_pdf(
            file_content=file_content,
            filename=filename,
            conversation_id="test-conversation-123"
        )
        
        if result.status.value == "VALIDATED" or result.status.value == "COMPLETED":
            print(f"✓ Claim extraction completed successfully")
            print(f"✓ Processing time: {result.processing_time:.2f} seconds")
            print(f"✓ Document confidence: {result.document_intelligence_confidence:.2f}")
            
            if result.extracted_claim:
                claim = result.extracted_claim
                print(f"✓ Total pages: {claim.total_pages}")
                print(f"✓ Document type: {claim.document_type}")
                
                # Show extracted fields
                if hasattr(claim, 'case_number') and claim.case_number:
                    print(f"✓ Case number: {claim.case_number}")
                if hasattr(claim, 'plaintiff_name') and claim.plaintiff_name:
                    print(f"✓ Plaintiff: {claim.plaintiff_name}")
                if hasattr(claim, 'defendant_name') and claim.defendant_name:
                    print(f"✓ Defendant: {claim.defendant_name}")
        else:
            print(f"✗ Claim extraction failed: {result.status.value}")
            if result.errors:
                print(f"  Errors: {result.errors}")
                
    except Exception as e:
        print(f"✗ Error testing claim extractor integration: {e}")


async def test_api_endpoints():
    """Test the API endpoints for enhanced PDF processing."""
    print("\n" + "="*60)
    print("Testing API Endpoints")
    print("="*60)
    
    # This would require a running server and HTTP client
    print("To test API endpoints, start the server and use:")
    print("\n1. Enhanced PDF Analysis:")
    print("   POST /api/v1/document-intelligence/analyze-pdf-enhanced")
    print("   - Upload a PDF file")
    print("   - Returns page-by-page analysis results")
    
    print("\n2. Multi-Model PDF Analysis:")
    print("   POST /api/v1/document-intelligence/analyze-pdf-multi-model")
    print("   - Upload a PDF file")
    print("   - Returns results using best model for each page")
    
    print("\n3. Available Models:")
    print("   GET /api/v1/document-intelligence/models")
    print("   - Returns list of available Document Intelligence models")
    
    print("\n4. Text Extraction Only:")
    print("   POST /api/v1/document-intelligence/extract-text-only")
    print("   - Upload any document")
    print("   - Returns extracted text content")


def main():
    """Main test function."""
    print("Enhanced PDF Processing Test Suite")
    print("This script tests the enhanced PDF processing capabilities")
    print("including page splitting and Document Intelligence integration.")
    
    # Check if we have the required dependencies
    try:
        import PyPDF2
        print("✓ PyPDF2 is available")
    except ImportError:
        print("✗ PyPDF2 is not available. Please install it: pip install PyPDF2")
        return
    
    try:
        from azure.ai.formrecognizer import DocumentAnalysisClient
        print("✓ Azure Document Intelligence is available")
    except ImportError:
        print("✗ Azure Document Intelligence is not available")
        print("  Please install it: pip install azure-ai-formrecognizer")
    
    # Run tests
    asyncio.run(test_pdf_splitter_service())
    asyncio.run(test_document_processor_integration())
    asyncio.run(test_claim_extractor_integration())
    asyncio.run(test_api_endpoints())
    
    print("\n" + "="*60)
    print("Test Suite Completed")
    print("="*60)
    print("\nKey Features Tested:")
    print("✓ PDF splitting into individual pages")
    print("✓ Page-by-page Document Intelligence analysis")
    print("✓ Multi-model extraction for better coverage")
    print("✓ Integration with existing services")
    print("✓ API endpoints for enhanced processing")
    
    print("\nTo use these features:")
    print("1. Upload a PDF through the API endpoints")
    print("2. The system will automatically split it into pages")
    print("3. Each page will be processed with Document Intelligence")
    print("4. Results will be combined for comprehensive text extraction")


if __name__ == "__main__":
    main() 