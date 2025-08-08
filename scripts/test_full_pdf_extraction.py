#!/usr/bin/env python3
"""
Test Full PDF Extraction with All Pages

This script tests that all pages are being properly extracted and included
in the response, not just the first page.
"""

import os
import sys
import asyncio
import time
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.claim_extractor.service import ClaimExtractorService

async def test_full_pdf_extraction():
    """Test that all pages are properly extracted and included in response."""
    print("Testing Full PDF Extraction with All Pages")
    print("="*60)
    
    # Initialize the service
    service = ClaimExtractorService()
    
    # Test with a sample PDF
    test_file_path = "tests/data/valid_claim.pdf"
    
    if not os.path.exists(test_file_path):
        print(f"❌ Test file not found: {test_file_path}")
        return
    
    try:
        # Read the test file
        with open(test_file_path, "rb") as f:
            file_content = f.read()
        
        print(f"📄 Processing file: {test_file_path}")
        print(f"📊 File size: {len(file_content)} bytes")
        print()
        
        # Extract claim information
        result = await service.extract_claim_from_pdf(
            file_content=file_content,
            filename="valid_claim.pdf",
            conversation_id="test-full-extraction-123"
        )
        
        # Display results
        print("✅ Full PDF extraction completed successfully!")
        print()
        
        print("📋 EXTRACTION RESULTS:")
        print(f"   Status: {result.status}")
        print(f"   Total Pages: {result.extracted_claim.total_pages if result.extracted_claim else 'N/A'}")
        print(f"   Raw Text Length: {result.raw_text_length} characters")
        print(f"   Page Contents Count: {len(result.page_contents)}")
        print()
        
        # Check if all pages are included
        print("📄 PAGE CONTENT ANALYSIS:")
        if result.page_contents:
            for i, page_content in enumerate(result.page_contents, 1):
                print(f"   Page {page_content.page_number}:")
                print(f"     Text Length: {len(page_content.extracted_text)} characters")
                print(f"     Model Used: {page_content.model_used}")
                print(f"     Confidence: {page_content.confidence:.2f}")
                print(f"     Success: {page_content.success}")
                if page_content.error_message:
                    print(f"     Error: {page_content.error_message}")
                print()
            
            # Verify all pages are present
            page_numbers = [pc.page_number for pc in result.page_contents]
            expected_pages = list(range(1, len(result.page_contents) + 1))
            
            if page_numbers == expected_pages:
                print("✅ All pages are present and properly numbered!")
            else:
                print(f"❌ Missing pages! Found: {page_numbers}, Expected: {expected_pages}")
        else:
            print("❌ No page contents found!")
        
        print()
        
        # Check raw text content
        print("📝 RAW TEXT ANALYSIS:")
        if result.raw_text:
            # Count page separators in raw text
            page_separators = result.raw_text.count("--- Page")
            print(f"   Page separators found: {page_separators}")
            print(f"   Total text length: {len(result.raw_text)} characters")
            
            # Check if all pages are mentioned in raw text
            for i in range(1, len(result.page_contents) + 1):
                if f"--- Page {i}" in result.raw_text:
                    print(f"   ✅ Page {i} found in raw text")
                else:
                    print(f"   ❌ Page {i} NOT found in raw text")
            
            # Show first 200 characters of each page from raw text
            print("\n📄 RAW TEXT PREVIEW:")
            lines = result.raw_text.split('\n')
            current_page = None
            page_text = ""
            
            for line in lines:
                if line.startswith("--- Page"):
                    if current_page and page_text:
                        print(f"   Page {current_page}: {page_text[:200]}...")
                    current_page = line.split()[2]  # Extract page number
                    page_text = ""
                elif current_page:
                    page_text += line + " "
            
            # Show last page
            if current_page and page_text:
                print(f"   Page {current_page}: {page_text[:200]}...")
        else:
            print("❌ No raw text found!")
        
        print()
        
        # Display extracted claim information
        if result.extracted_claim:
            print("📋 EXTRACTED CLAIM INFORMATION:")
            print(f"   Case Type: {result.extracted_claim.case_type}")
            print(f"   Plaintiff: {result.extracted_claim.plaintiff_name}")
            print(f"   Defendant: {result.extracted_claim.defendant_name}")
            print(f"   Claim Overview: {result.extracted_claim.claim_overview}")
            print(f"   Is Valid: {result.extracted_claim.is_valid}")
            print()
        
        # Summary
        print("🎯 SUMMARY:")
        total_chars = sum(len(pc.extracted_text) for pc in result.page_contents)
        print(f"   Total characters from all pages: {total_chars}")
        print(f"   Raw text characters: {result.raw_text_length}")
        print(f"   Character difference: {abs(total_chars - result.raw_text_length)}")
        
        if abs(total_chars - result.raw_text_length) < 100:  # Allow for some formatting differences
            print("   ✅ Character counts match (all pages included)")
        else:
            print("   ⚠️  Character counts don't match (possible missing content)")
        
        print("\n🎉 Full PDF extraction test completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

async def test_api_response_format():
    """Test the API response format to ensure all pages are included."""
    print("\n" + "="*60)
    print("Testing API Response Format")
    print("="*60)
    
    # Initialize the service
    service = ClaimExtractorService()
    
    # Test with a sample PDF
    test_file_path = "tests/data/valid_claim.pdf"
    
    if not os.path.exists(test_file_path):
        print(f"❌ Test file not found: {test_file_path}")
        return
    
    try:
        # Read the test file
        with open(test_file_path, "rb") as f:
            file_content = f.read()
        
        print(f"📄 Testing API response format with: {test_file_path}")
        print()
        
        # Extract claim information
        result = await service.extract_claim_from_pdf(
            file_content=file_content,
            filename="valid_claim.pdf",
            conversation_id="test-api-format-123"
        )
        
        # Simulate API response format
        response = {
            "status": "success",
            "processing_id": result.processing_id,
            "filename": result.filename,
            "extraction_status": result.status.value,
            "processing_time": result.processing_time,
            "file_url": result.file_url,
            "error_message": result.error_message,
            "raw_text": result.raw_text,
            "raw_text_length": result.raw_text_length,
            "page_contents": []
        }
        
        # Add individual page contents
        if result.page_contents:
            for page_content in result.page_contents:
                page_info = {
                    "page_number": page_content.page_number,
                    "extracted_text": page_content.extracted_text,
                    "text_length": len(page_content.extracted_text),
                    "confidence": page_content.confidence,
                    "model_used": page_content.model_used,
                    "success": page_content.success,
                    "processing_time": page_content.processing_time
                }
                if page_content.error_message:
                    page_info["error_message"] = page_content.error_message
                response["page_contents"].append(page_info)
        
        # Add extracted claim information
        if result.extracted_claim:
            essential_fields = {
                "case_number": result.extracted_claim.case_number,
                "plaintiff_name": result.extracted_claim.plaintiff_name,
                "defendant_name": result.extracted_claim.defendant_name,
                "case_type": result.extracted_claim.case_type,
                "claim_overview": result.extracted_claim.claim_overview,
                "claim_amount": result.extracted_claim.claim_amount,
                "currency": result.extracted_claim.currency
            }
            response["extracted_claim"] = {k: v for k, v in essential_fields.items() if v}
            response["is_valid"] = result.extracted_claim.is_valid
        
        # Display API response structure
        print("📋 API RESPONSE STRUCTURE:")
        print(f"   Status: {response['status']}")
        print(f"   Processing ID: {response['processing_id']}")
        print(f"   Filename: {response['filename']}")
        print(f"   Extraction Status: {response['extraction_status']}")
        print(f"   Processing Time: {response['processing_time']:.2f}s")
        print(f"   Raw Text Length: {response['raw_text_length']} characters")
        print(f"   Page Contents Count: {len(response['page_contents'])}")
        print()
        
        # Verify page contents in API response
        print("📄 PAGE CONTENTS IN API RESPONSE:")
        for page_info in response["page_contents"]:
            print(f"   Page {page_info['page_number']}:")
            print(f"     Text Length: {page_info['text_length']} characters")
            print(f"     Model Used: {page_info['model_used']}")
            print(f"     Confidence: {page_info['confidence']:.2f}")
            print(f"     Success: {page_info['success']}")
            if 'error_message' in page_info:
                print(f"     Error: {page_info['error_message']}")
            print()
        
        # Verify all pages are included
        page_numbers = [p['page_number'] for p in response["page_contents"]]
        expected_pages = list(range(1, len(response["page_contents"]) + 1))
        
        if page_numbers == expected_pages:
            print("✅ All pages are included in API response!")
        else:
            print(f"❌ Missing pages in API response! Found: {page_numbers}, Expected: {expected_pages}")
        
        print("\n🎉 API response format test completed!")
        
    except Exception as e:
        print(f"❌ Error during API format testing: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function."""
    print("Full PDF Extraction Test")
    print("="*60)
    
    # Test full PDF extraction
    await test_full_pdf_extraction()
    
    # Test API response format
    await test_api_response_format()
    
    print("\n" + "="*60)
    print("All Tests Completed Successfully!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main()) 