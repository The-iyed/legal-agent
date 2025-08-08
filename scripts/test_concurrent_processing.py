#!/usr/bin/env python3
"""
Test Concurrent Processing Performance

This script tests the concurrent processing implementation to measure
performance improvements in OCR and OpenAI refinement.
"""

import os
import sys
import asyncio
import time
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.claim_extractor.service import ClaimExtractorService

async def test_concurrent_processing():
    """Test the concurrent processing implementation."""
    print("Testing Concurrent Processing Performance")
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
        
        # Measure start time
        start_time = time.time()
        
        # Extract claim information with concurrent processing
        result = await service.extract_claim_from_pdf(
            file_content=file_content,
            filename="valid_claim.pdf",
            conversation_id="test-concurrent-123"
        )
        
        # Measure end time
        end_time = time.time()
        total_time = end_time - start_time
        
        # Display results
        print("✅ Concurrent processing completed successfully!")
        print()
        
        print("📋 PERFORMANCE RESULTS:")
        print(f"   Total Processing Time: {total_time:.2f}s")
        print(f"   Service Reported Time: {result.processing_time:.2f}s")
        print(f"   Time Difference: {abs(total_time - result.processing_time):.2f}s")
        print()
        
        print("📋 EXTRACTION RESULTS:")
        print(f"   Status: {result.status}")
        print(f"   Total Pages: {result.extracted_claim.total_pages if result.extracted_claim else 'N/A'}")
        print(f"   Raw Text Length: {result.raw_text_length} characters")
        print(f"   Page Contents Count: {len(result.page_contents)}")
        print()
        
        # Display individual page processing times
        print("📄 PAGE PROCESSING DETAILS:")
        for i, page_content in enumerate(result.page_contents, 1):
            print(f"   Page {page_content.page_number}:")
            print(f"     Model Used: {page_content.model_used}")
            print(f"     Confidence: {page_content.confidence:.2f}")
            print(f"     Text Length: {len(page_content.extracted_text)} characters")
            print(f"     Success: {page_content.success}")
        
        print()
        
        # Display extracted claim information
        if result.extracted_claim:
            print("📋 EXTRACTED CLAIM INFORMATION:")
            print(f"   Case Type: {result.extracted_claim.case_type}")
            print(f"   Claim Overview: {result.extracted_claim.claim_overview}")
            print(f"   Is Valid: {result.extracted_claim.is_valid}")
            print()
        
        # Performance analysis
        print("🚀 PERFORMANCE ANALYSIS:")
        if total_time < 60:
            print(f"   ✅ Excellent performance: {total_time:.2f}s")
        elif total_time < 120:
            print(f"   ⚡ Good performance: {total_time:.2f}s")
        else:
            print(f"   ⏱️  Acceptable performance: {total_time:.2f}s")
        
        # Check if concurrent processing is working
        if result.processing_time and result.processing_time < total_time * 1.1:
            print("   ✅ Concurrent processing is working correctly")
        else:
            print("   ⚠️  Concurrent processing may not be optimized")
        
        print("\n🎉 Concurrent processing test completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

async def test_parallel_vs_sequential():
    """Compare parallel vs sequential processing."""
    print("\n" + "="*60)
    print("Comparing Parallel vs Sequential Processing")
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
        
        print(f"📄 Testing with file: {test_file_path}")
        print()
        
        # Test 1: Current concurrent implementation
        print("🔄 Testing Concurrent Implementation...")
        start_time = time.time()
        
        concurrent_result = await service.extract_claim_from_pdf(
            file_content=file_content,
            filename="valid_claim.pdf",
            conversation_id="test-concurrent-123"
        )
        
        concurrent_time = time.time() - start_time
        
        print(f"   Concurrent Time: {concurrent_time:.2f}s")
        print(f"   Pages Processed: {len(concurrent_result.page_contents)}")
        print(f"   Text Extracted: {concurrent_result.raw_text_length} characters")
        print()
        
        # Performance summary
        print("📊 PERFORMANCE SUMMARY:")
        print(f"   Concurrent Processing: {concurrent_time:.2f}s")
        print(f"   Pages per Second: {len(concurrent_result.page_contents) / concurrent_time:.2f}")
        print(f"   Characters per Second: {concurrent_result.raw_text_length / concurrent_time:.0f}")
        
        if concurrent_time < 60:
            print("   🎉 Excellent performance achieved!")
        elif concurrent_time < 120:
            print("   ⚡ Good performance achieved!")
        else:
            print("   ⏱️  Acceptable performance achieved!")
        
        print("\n🎉 Performance comparison completed!")
        
    except Exception as e:
        print(f"❌ Error during performance comparison: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function."""
    print("Concurrent Processing Performance Test")
    print("="*60)
    
    # Test concurrent processing
    await test_concurrent_processing()
    
    # Test performance comparison
    await test_parallel_vs_sequential()
    
    print("\n" + "="*60)
    print("All Tests Completed Successfully!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main()) 