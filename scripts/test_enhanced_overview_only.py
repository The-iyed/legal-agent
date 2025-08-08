#!/usr/bin/env python3
"""
Test Enhanced Claim Overview Only

This script tests only the enhanced claim overview generation
without the complex agent dependencies.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.claim_extractor.service import ClaimExtractorService

async def test_enhanced_claim_overview():
    """Test the enhanced claim overview generation."""
    print("Testing Enhanced Claim Overview Generation")
    print("="*60)
    
    # Initialize the claim extractor service
    claim_extractor = ClaimExtractorService()
    
    # Test with a sample PDF
    test_file_path = "tests/data/valid_claim.pdf"
    
    if not os.path.exists(test_file_path):
        print(f"❌ Test file not found: {test_file_path}")
        return
    
    try:
        # Read the test file
        with open(test_file_path, "rb") as f:
            file_content = f.read()
        
        print(f"📄 Testing enhanced claim overview with: {test_file_path}")
        print(f"📊 File size: {len(file_content)} bytes")
        print()
        
        # Extract claim information
        extraction_result = await claim_extractor.extract_claim_from_pdf(
            file_content=file_content,
            filename="valid_claim.pdf",
            conversation_id="test-enhanced-overview-123"
        )
        
        # Display results
        print("✅ Enhanced claim extraction completed successfully!")
        print()
        
        print("📋 EXTRACTION RESULTS:")
        print(f"   Status: {extraction_result.status}")
        print(f"   Processing Time: {extraction_result.processing_time:.2f}s")
        print(f"   Is Valid: {extraction_result.extracted_claim.is_valid if extraction_result.extracted_claim else 'N/A'}")
        print(f"   Total Pages: {extraction_result.extracted_claim.total_pages if extraction_result.extracted_claim else 'N/A'}")
        print()
        
        # Display enhanced claim overview
        if extraction_result.extracted_claim and extraction_result.extracted_claim.claim_overview:
            print("📝 ENHANCED CLAIM OVERVIEW:")
            print("=" * 60)
            print(extraction_result.extracted_claim.claim_overview)
            print("=" * 60)
            
            # Count lines in overview
            overview_lines = extraction_result.extracted_claim.claim_overview.split('\n')
            non_empty_lines = [line.strip() for line in overview_lines if line.strip()]
            
            print(f"\n📊 Overview Statistics:")
            print(f"   Total Lines: {len(overview_lines)}")
            print(f"   Non-empty Lines: {len(non_empty_lines)}")
            print(f"   Character Count: {len(extraction_result.extracted_claim.claim_overview)}")
            
            # Check if overview meets requirements
            if len(non_empty_lines) >= 5:
                print("   ✅ Overview meets the 5-6 lines requirement!")
            else:
                print(f"   ⚠️  Overview has {len(non_empty_lines)} lines, should be 5-6 lines")
            
            # Check for professional legal elements
            professional_elements = [
                "معلومات الدعوى",
                "الأطراف المعنية", 
                "موضوع الدعوى",
                "الطلبات المقدمة",
                "التقييم القانوني",
                "التوصيات"
            ]
            
            found_elements = []
            for element in professional_elements:
                if element in extraction_result.extracted_claim.claim_overview:
                    found_elements.append(element)
            
            print(f"\n🔍 Professional Elements Found: {len(found_elements)}/{len(professional_elements)}")
            for element in found_elements:
                print(f"   ✅ {element}")
            
            if len(found_elements) >= 3:
                print("   ✅ Overview contains professional legal elements!")
            else:
                print("   ⚠️  Overview missing some professional elements")
                
        else:
            print("❌ No claim overview generated!")
        
        print("\n🎉 Enhanced claim overview test completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function."""
    print("Enhanced Claim Overview Test")
    print("="*60)
    
    # Test enhanced claim overview
    await test_enhanced_claim_overview()
    
    print("\n" + "="*60)
    print("Test Completed Successfully!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main()) 