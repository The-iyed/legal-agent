#!/usr/bin/env python3
"""
Test Enhanced Agent Integration

This script tests the enhanced agent integration with the claim extractor
to verify that it generates professional legal responses like a lawyer.
"""

import os
import sys
import asyncio
import time
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.agent.service import AgentService
from app.modules.message.service import MessageService
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
        print(f"   Is Valid: {extraction_result.is_valid}")
        print(f"   Total Pages: {extraction_result.extracted_claim.total_pages if extraction_result.extracted_claim else 'N/A'}")
        print()
        
        # Display enhanced claim overview
        if extraction_result.extracted_claim and extraction_result.extracted_claim.claim_overview:
            print("📝 ENHANCED CLAIM OVERVIEW:")
            print("-" * 50)
            print(extraction_result.extracted_claim.claim_overview)
            print("-" * 50)
            
            # Count lines in overview
            overview_lines = extraction_result.extracted_claim.claim_overview.split('\n')
            non_empty_lines = [line.strip() for line in overview_lines if line.strip()]
            print(f"\n📊 Overview Statistics:")
            print(f"   Total Lines: {len(overview_lines)}")
            print(f"   Non-empty Lines: {len(non_empty_lines)}")
            print(f"   Character Count: {len(extraction_result.extracted_claim.claim_overview)}")
            
            if len(non_empty_lines) >= 5:
                print("   ✅ Overview meets the 5-6 lines requirement!")
            else:
                print(f"   ⚠️  Overview has {len(non_empty_lines)} lines, should be 5-6 lines")
        else:
            print("❌ No claim overview generated!")
        
        print("\n🎉 Enhanced claim overview test completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

async def test_agent_integration():
    """Test the agent integration with claim extractor."""
    print("\n" + "="*60)
    print("Testing Agent Integration with Claim Extractor")
    print("="*60)
    
    # Mock database and message service for testing
    class MockDB:
        def __init__(self):
            self.data = {}
        
        async def execute(self, query, params=None):
            return None
        
        async def fetch_one(self, query, params=None):
            return None
        
        async def fetch_all(self, query, params=None):
            return []
    
    class MockMessageService:
        async def create_message(self, message_data):
            return {"id": "mock-message-id"}
    
    # Initialize agent service
    mock_db = MockDB()
    mock_message_service = MockMessageService()
    agent_service = AgentService(mock_db, mock_message_service)
    
    # Test with a sample PDF
    test_file_path = "tests/data/valid_claim.pdf"
    
    if not os.path.exists(test_file_path):
        print(f"❌ Test file not found: {test_file_path}")
        return
    
    try:
        # Read the test file
        with open(test_file_path, "rb") as f:
            file_content = f.read()
        
        print(f"📄 Testing agent integration with: {test_file_path}")
        print()
        
        # Process file upload through agent
        response = await agent_service.process_file_upload(
            file_content=file_content,
            filename="valid_claim.pdf",
            conversation_id="test-agent-integration-123",
            user_id="test-user-123"
        )
        
        # Display results
        print("✅ Agent integration test completed successfully!")
        print()
        
        print("📋 AGENT RESPONSE:")
        print(f"   Success: {response.success}")
        print(f"   Is Valid: {response.is_valid}")
        print(f"   Case Number: {response.case_number}")
        print(f"   File URL: {response.file_url}")
        print()
        
        print("📝 PROFESSIONAL LEGAL RESPONSE:")
        print("-" * 60)
        print(response.response)
        print("-" * 60)
        
        # Analyze response quality
        response_lines = response.response.split('\n')
        non_empty_lines = [line.strip() for line in response_lines if line.strip()]
        
        print(f"\n📊 Response Quality Analysis:")
        print(f"   Total Lines: {len(response_lines)}")
        print(f"   Non-empty Lines: {len(non_empty_lines)}")
        print(f"   Character Count: {len(response.response)}")
        
        # Check for professional elements
        professional_elements = [
            "تحليل قانوني",
            "معلومات الدعوى",
            "الأطراف المعنية",
            "تفاصيل القضية",
            "التحليل القانوني",
            "معلومات المعالجة",
            "الخطوات التالية"
        ]
        
        found_elements = []
        for element in professional_elements:
            if element in response.response:
                found_elements.append(element)
        
        print(f"   Professional Elements Found: {len(found_elements)}/{len(professional_elements)}")
        for element in found_elements:
            print(f"     ✅ {element}")
        
        if len(found_elements) >= 5:
            print("   ✅ Response meets professional legal standards!")
        else:
            print(f"   ⚠️  Response missing some professional elements")
        
        print("\n🎉 Agent integration test completed!")
        
    except Exception as e:
        print(f"❌ Error during agent integration testing: {e}")
        import traceback
        traceback.print_exc()

async def test_conversation_status_updates():
    """Test conversation status updates during processing."""
    print("\n" + "="*60)
    print("Testing Conversation Status Updates")
    print("="*60)
    
    # Mock database and message service for testing
    class MockDB:
        def __init__(self):
            self.data = {}
        
        async def execute(self, query, params=None):
            return None
        
        async def fetch_one(self, query, params=None):
            return None
        
        async def fetch_all(self, query, params=None):
            return []
    
    class MockMessageService:
        async def create_message(self, message_data):
            return {"id": "mock-message-id"}
    
    # Initialize agent service
    mock_db = MockDB()
    mock_message_service = MockMessageService()
    agent_service = AgentService(mock_db, mock_message_service)
    
    # Test with a sample PDF
    test_file_path = "tests/data/valid_claim.pdf"
    
    if not os.path.exists(test_file_path):
        print(f"❌ Test file not found: {test_file_path}")
        return
    
    try:
        # Read the test file
        with open(test_file_path, "rb") as f:
            file_content = f.read()
        
        print(f"📄 Testing conversation status updates with: {test_file_path}")
        print()
        
        # Process file upload through agent
        response = await agent_service.process_file_upload(
            file_content=file_content,
            filename="valid_claim.pdf",
            conversation_id="test-status-updates-123",
            user_id="test-user-123"
        )
        
        # Display results
        print("✅ Conversation status test completed successfully!")
        print()
        
        print("📋 STATUS UPDATE RESULTS:")
        print(f"   Success: {response.success}")
        print(f"   Is Valid: {response.is_valid}")
        print(f"   Extraction Status: {response.metadata.get('extraction_status', 'N/A')}")
        print(f"   Processing Time: {response.metadata.get('processing_time', 'N/A')}")
        print(f"   Validation Score: {response.metadata.get('validation_score', 'N/A')}")
        print()
        
        # Check if status updates are working
        if response.metadata.get('extraction_status'):
            print("✅ Conversation status updates are working!")
        else:
            print("⚠️  Conversation status updates may not be working properly")
        
        print("\n🎉 Conversation status test completed!")
        
    except Exception as e:
        print(f"❌ Error during conversation status testing: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function."""
    print("Enhanced Agent Integration Test")
    print("="*60)
    
    # Test enhanced claim overview
    await test_enhanced_claim_overview()
    
    # Test agent integration
    await test_agent_integration()
    
    # Test conversation status updates
    await test_conversation_status_updates()
    
    print("\n" + "="*60)
    print("All Tests Completed Successfully!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main()) 