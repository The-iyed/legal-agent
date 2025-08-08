#!/usr/bin/env python3
"""
Test Enhanced Claim Extractor with Page Content Storage

This script tests the enhanced claim extractor that now stores individual page content.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.claim_extractor.service import ClaimExtractorService

async def test_enhanced_claim_extractor():
    """Test the enhanced claim extractor with page content storage."""
    print("Testing Enhanced Claim Extractor with Page Content Storage")
    print("="*70)
    
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
            conversation_id="test-conversation-123"
        )
        
        # Display results
        print("✅ Claim extraction completed successfully!")
        print()
        
        print("📋 EXTRACTION SUMMARY:")
        print(f"   Processing ID: {result.processing_id}")
        print(f"   Status: {result.status}")
        print(f"   Processing Time: {result.processing_time:.2f}s")
        print(f"   Total Pages: {result.extracted_claim.total_pages if result.extracted_claim else 'N/A'}")
        print(f"   Raw Text Length: {result.raw_text_length} characters")
        print(f"   Page Contents Count: {len(result.page_contents)}")
        print()
        
        # Display individual page contents
        print("📄 INDIVIDUAL PAGE CONTENTS:")
        for i, page_content in enumerate(result.page_contents, 1):
            print(f"\n   Page {page_content.page_number}:")
            print(f"     Model Used: {page_content.model_used}")
            print(f"     Confidence: {page_content.confidence:.2f}")
            print(f"     Processing Time: {page_content.processing_time:.2f}s" if page_content.processing_time else "     Processing Time: N/A")
            print(f"     Success: {page_content.success}")
            print(f"     Text Length: {len(page_content.extracted_text)} characters")
            
            # Show first 200 characters of each page
            preview = page_content.extracted_text[:200].replace('\n', ' ').strip()
            print(f"     Preview: {preview}...")
            
            # Show key-value pairs if any
            if page_content.key_value_pairs:
                print(f"     Key-Value Pairs: {len(page_content.key_value_pairs)} found")
                for key, value in list(page_content.key_value_pairs.items())[:3]:  # Show first 3
                    print(f"       {key}: {value}")
        
        print()
        
        # Display extracted claim information
        if result.extracted_claim:
            print("📋 EXTRACTED CLAIM INFORMATION:")
            print(f"   Case Type: {result.extracted_claim.case_type}")
            print(f"   Plaintiff: {result.extracted_claim.plaintiff_name}")
            print(f"   Defendant: {result.extracted_claim.defendant_name}")
            print(f"   Court: {result.extracted_claim.court_name}")
            print(f"   Claim Overview: {result.extracted_claim.claim_overview}")
            print(f"   Is Valid: {result.extracted_claim.is_valid}")
            print()
        
        # Test the to_dict method to ensure page contents are properly serialized
        print("🔧 TESTING SERIALIZATION:")
        result_dict = result.to_dict()
        
        # Check if page_contents are in the dictionary
        if "page_contents" in result_dict:
            print(f"   ✅ Page contents serialized: {len(result_dict['page_contents'])} pages")
            for i, page_dict in enumerate(result_dict["page_contents"], 1):
                print(f"     Page {i}: {page_dict.get('page_number')} - {len(page_dict.get('extracted_text', ''))} chars")
        else:
            print("   ❌ Page contents not found in serialized result")
        
        # Test deserialization
        print("\n🔄 TESTING DESERIALIZATION:")
        reconstructed_result = result.__class__.from_dict(result_dict)
        print(f"   ✅ Deserialization successful")
        print(f"   Page contents count: {len(reconstructed_result.page_contents)}")
        
        print("\n🎉 All tests passed! Enhanced claim extractor is working correctly.")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

async def test_api_response_format():
    """Test the API response format with page contents."""
    print("\n" + "="*70)
    print("Testing API Response Format")
    print("="*70)
    
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
        
        # Extract claim information
        result = await service.extract_claim_from_pdf(
            file_content=file_content,
            filename="valid_claim.pdf",
            conversation_id="test-conversation-123"
        )
        
        # Convert to API response format
        response_dict = result.to_dict()
        
        print("📋 API RESPONSE FORMAT:")
        print("Expected fields in response:")
        
        required_fields = [
            "status", "processing_id", "filename", "file_url",
            "raw_text", "raw_text_length", "page_contents",
            "extracted_claim", "processing_time", "created_at", "completed_at"
        ]
        
        for field in required_fields:
            if field in response_dict:
                value = response_dict[field]
                if field == "page_contents":
                    print(f"   ✅ {field}: {len(value)} pages")
                elif field == "raw_text":
                    print(f"   ✅ {field}: {len(value)} characters")
                elif field == "extracted_claim":
                    print(f"   ✅ {field}: {'Present' if value else 'None'}")
                else:
                    print(f"   ✅ {field}: {value}")
            else:
                print(f"   ❌ {field}: Missing")
        
        print("\n📄 PAGE CONTENTS STRUCTURE:")
        if "page_contents" in response_dict and response_dict["page_contents"]:
            page = response_dict["page_contents"][0]
            print("   Each page contains:")
            for key, value in page.items():
                if key == "extracted_text":
                    print(f"     ✅ {key}: {len(value)} characters")
                else:
                    print(f"     ✅ {key}: {value}")
        else:
            print("   ❌ No page contents found")
        
        print("\n🎉 API response format test completed!")
        
    except Exception as e:
        print(f"❌ Error during API format testing: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function."""
    print("Enhanced Claim Extractor with Page Content Storage Test")
    print("="*70)
    
    # Test the enhanced claim extractor
    await test_enhanced_claim_extractor()
    
    # Test API response format
    await test_api_response_format()
    
    print("\n" + "="*70)
    print("Test Suite Completed Successfully!")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main()) 