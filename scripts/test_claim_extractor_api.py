#!/usr/bin/env python3
"""
Test Script for Claim Extractor API

This script demonstrates how to use the new claim extractor API endpoints
for testing and validation.
"""

import requests
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1/claim-extractor"


def test_health_check():
    """Test the health check endpoint."""
    print("🏥 Testing Health Check...")
    
    try:
        response = requests.get(f"{API_BASE}/health")
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Health Status: {data['status']}")
        print(f"📊 Components: {data['components']}")
        print(f"🔧 Services: {data['services']}")
        
        return data
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return None


def test_sample_data():
    """Test the sample data endpoint."""
    print("\n📋 Testing Sample Data...")
    
    try:
        response = requests.get(f"{API_BASE}/sample-data")
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Sample data retrieved")
        print(f"📝 Sample text length: {len(data['sample_text'])} characters")
        print(f"📊 Sample claim fields: {len(data['sample_claim'])} fields")
        
        return data
        
    except Exception as e:
        print(f"❌ Sample data failed: {e}")
        return None


def test_process_text(sample_text: str):
    """Test the text processing endpoint."""
    print("\n🧠 Testing Text Processing...")
    
    try:
        response = requests.post(
            f"{API_BASE}/process-text",
            json={"text": sample_text}
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Text processing successful")
        print(f"📊 Extracted fields: {data['extracted_fields']}")
        print(f"🏷️ Field names: {data['field_names']}")
        print(f"📄 Sections count: {data['sections_count']}")
        
        # Show some extracted data
        if data['structured_data']:
            print("📋 Sample extracted data:")
            for field, value in list(data['structured_data'].items())[:5]:
                print(f"   {field}: {value}")
        
        return data
        
    except Exception as e:
        print(f"❌ Text processing failed: {e}")
        return None


def test_validate_claim(sample_claim: Dict[str, Any]):
    """Test the claim validation endpoint."""
    print("\n✅ Testing Claim Validation...")
    
    try:
        response = requests.post(
            f"{API_BASE}/validate",
            json=sample_claim
        )
        response.raise_for_status()
        
        data = response.json()
        validation = data['validation_result']
        summary = data['summary']
        
        print(f"✅ Validation successful")
        print(f"📊 Validation score: {validation['score']:.2f}")
        print(f"✅ Is valid: {validation['is_valid']}")
        print(f"🎯 Confidence: {validation['confidence']:.2f}")
        print(f"❌ Errors: {len(validation['errors'])}")
        print(f"⚠️ Warnings: {len(validation['warnings'])}")
        print(f"📈 Quality level: {summary['quality_level']}")
        
        if validation['errors']:
            print("❌ Validation errors:")
            for error in validation['errors']:
                print(f"   - {error}")
        
        if validation['warnings']:
            print("⚠️ Validation warnings:")
            for warning in validation['warnings']:
                print(f"   - {warning}")
        
        return data
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return None


def test_refine_with_openai(sample_text: str, sample_claim: Dict[str, Any]):
    """Test the OpenAI refinement endpoint."""
    print("\n🤖 Testing OpenAI Refinement...")
    
    try:
        payload = {
            "raw_text": sample_text,
            "extracted_claim": sample_claim
        }
        
        response = requests.post(
            f"{API_BASE}/refine",
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Refinement successful")
        print(f"📝 Refined response length: {data['refined_response_length']}")
        print(f"📄 Legal summary length: {data['legal_summary_length']}")
        print(f"🔧 OpenAI available: {data['openai_available']}")
        
        # Show a preview of the refined response
        if data['refined_response']:
            preview = data['refined_response'][:200] + "..." if len(data['refined_response']) > 200 else data['refined_response']
            print(f"📋 Refined response preview: {preview}")
        
        return data
        
    except Exception as e:
        print(f"❌ Refinement failed: {e}")
        return None


def test_file_upload():
    """Test the file upload endpoint."""
    print("\n📁 Testing File Upload...")
    
    try:
        # Create a simple test file
        test_file_path = "test_claim.pdf"
        
        # Check if we have a test PDF file
        if not os.path.exists(test_file_path):
            print(f"⚠️ Test file {test_file_path} not found, creating minimal PDF...")
            create_minimal_pdf(test_file_path)
        
        with open(test_file_path, 'rb') as f:
            files = {'file': (test_file_path, f, 'application/pdf')}
            data = {'conversation_id': 'test_conversation_123'}
            
            response = requests.post(
                f"{API_BASE}/upload-test",
                files=files,
                data=data
            )
            response.raise_for_status()
        
        data = response.json()
        print(f"✅ File upload successful")
        print(f"📁 File URL: {data['file_url']}")
        print(f"📊 File size: {data['file_size']} bytes")
        print(f"🔧 Storage available: {data['storage_available']}")
        print(f"📋 Files count: {data['files_count']}")
        
        return data
        
    except Exception as e:
        print(f"❌ File upload failed: {e}")
        return None


def test_complete_extraction():
    """Test the complete extraction endpoint."""
    print("\n🚀 Testing Complete Extraction...")
    
    try:
        # Create a simple test file
        test_file_path = "test_claim.pdf"
        
        # Check if we have a test PDF file
        if not os.path.exists(test_file_path):
            print(f"⚠️ Test file {test_file_path} not found, creating minimal PDF...")
            create_minimal_pdf(test_file_path)
        
        with open(test_file_path, 'rb') as f:
            files = {'file': (test_file_path, f, 'application/pdf')}
            data = {'conversation_id': 'test_conversation_123'}
            
            response = requests.post(
                f"{API_BASE}/extract",
                files=files,
                data=data
            )
            response.raise_for_status()
        
        data = response.json()
        print(f"✅ Complete extraction successful")
        print(f"🆔 Processing ID: {data['processing_id']}")
        print(f"📊 Status: {data['extraction_status']}")
        print(f"⏱️ Processing time: {data['processing_time']:.2f}s")
        print(f"📁 File URL: {data['file_url']}")
        
        # Show confidence scores
        print(f"🎯 Document Intelligence confidence: {data.get('document_intelligence_confidence', 'N/A')}")
        print(f"🤖 OpenAI confidence: {data.get('openai_confidence', 'N/A')}")
        
        # Show extracted claim info
        if data.get('extracted_claim'):
            claim = data['extracted_claim']
            print(f"📋 Extracted claim info:")
            print(f"   Case number: {claim.get('case_number', 'N/A')}")
            print(f"   Plaintiff: {claim.get('plaintiff_name', 'N/A')}")
            print(f"   Defendant: {claim.get('defendant_name', 'N/A')}")
            print(f"   Court: {claim.get('court_name', 'N/A')}")
            print(f"   Is valid: {claim.get('is_valid', 'N/A')}")
            print(f"   Validation score: {claim.get('processing_confidence', 'N/A')}")
        
        return data
        
    except Exception as e:
        print(f"❌ Complete extraction failed: {e}")
        return None


def create_minimal_pdf(file_path: str):
    """Create a minimal PDF file for testing."""
    try:
        # Try to use reportlab
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from io import BytesIO
        
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Add legal document content
        p.drawString(100, 750, "صحيفة الدعوى")
        p.drawString(100, 720, "رقم الطلب: 1383951")
        p.drawString(100, 690, "اسم المدعي: عبير احمد سعيد العمودي")
        p.drawString(100, 660, "اسم المدعى عليه: أمانة منطقة الرياض")
        p.drawString(100, 630, "المحكمة: المحكمة الإدارية بالرياض")
        
        p.save()
        pdf_content = buffer.getvalue()
        buffer.close()
        
        with open(file_path, 'wb') as f:
            f.write(pdf_content)
        
        print(f"✅ Created test PDF: {file_path}")
        
    except ImportError:
        # Create a very basic PDF manually
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Sample Document) Tj\nET\nendstream\nendobj\n\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000204 00000 n\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n297\n%%EOF'
        
        with open(file_path, 'wb') as f:
            f.write(pdf_content)
        
        print(f"✅ Created minimal test PDF: {file_path}")


def run_all_tests():
    """Run all API tests."""
    print("🧪 Starting Claim Extractor API Tests")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Health Check
    results['health'] = test_health_check()
    
    # Test 2: Sample Data
    sample_data = test_sample_data()
    results['sample_data'] = sample_data
    
    if sample_data:
        # Test 3: Text Processing
        results['text_processing'] = test_process_text(sample_data['sample_text'])
        
        # Test 4: Claim Validation
        results['validation'] = test_validate_claim(sample_data['sample_claim'])
        
        # Test 5: OpenAI Refinement
        results['refinement'] = test_refine_with_openai(
            sample_data['sample_text'], 
            sample_data['sample_claim']
        )
    
    # Test 6: File Upload
    results['file_upload'] = test_file_upload()
    
    # Test 7: Complete Extraction
    results['complete_extraction'] = test_complete_extraction()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 API TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    successful_tests = sum(1 for result in results.values() if result is not None)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result is not None else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    print(f"\n🎯 Success Rate: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
    
    if successful_tests == total_tests:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed. Check the logs above for details.")
    
    return results


if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code != 200:
            print(f"❌ Server not running at {BASE_URL}")
            print("Please start the server with: python3 -m uvicorn app.main:app --reload")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to server at {BASE_URL}")
        print("Please start the server with: python3 -m uvicorn app.main:app --reload")
        sys.exit(1)
    
    # Run tests
    run_all_tests() 