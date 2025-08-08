#!/usr/bin/env python3
"""
Test Script for Claim Extractor Module

This script tests the complete claim extraction pipeline including:
- Text processing
- OpenAI refinement
- Storage management
- Validation
- Complete claim extraction service
"""

import sys
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import json
from pathlib import Path
import tempfile

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.modules.claim_extractor import (
    ClaimExtractorService,
    ClaimInfo,
    ExtractionResult,
    ProcessingStatus
)
from app.modules.claim_extractor.text_processor import TextProcessor
from app.modules.claim_extractor.openai_refiner import OpenAIRefiner
from app.modules.claim_extractor.storage_manager import StorageManager
from app.modules.claim_extractor.validator import ClaimValidator, ValidationResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClaimExtractorTester:
    """Test suite for the claim extractor module."""
    
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
        
    def _create_sample_pdf_content(self) -> bytes:
        """Create a sample PDF file for testing."""
        try:
            # Try to use reportlab to create a PDF
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from io import BytesIO
            
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            
            # Add legal document content
            p.drawString(100, 750, "صحيفة الدعوى")
            p.drawString(100, 720, "بيانات صحيفة الدعوى:")
            p.drawString(100, 690, "رقم الطلب: ١٣٨٣٩٥١")
            p.drawString(100, 660, "التاريخ: ١٤٤٤/٠٣/١٩")
            p.drawString(100, 630, "اسم المدعي: عبير احمد سعيد العمودي")
            p.drawString(100, 600, "اسم المدعى عليه: أمانة منطقة الرياض")
            p.drawString(100, 570, "رقم الجوال: ٠٥٤٨٠٠٦٧٠٠")
            p.drawString(100, 540, "البريد الإلكتروني: maabeer@gmail.com")
            
            p.drawString(100, 510, "معلومات المحكمة:")
            p.drawString(100, 480, "المحكمة: المحكمة الإدارية بالرياض")
            p.drawString(100, 450, "نوع الدعوى: دعوى إدارية")
            p.drawString(100, 420, "موضوع الدعوى: طلب إلغاء قرار إداري")
            
            p.drawString(100, 390, "معلومات اضافية:")
            p.drawString(100, 360, "رقم القرار: ٠٠٠٠٠٣٦٥٧٨٤٦")
            p.drawString(100, 330, "رقم التظلم: ٣٨٠٥٤٨٢")
            p.drawString(100, 300, "رقم المخالفة: ١٠٠٠٠٠٠٣٦٥٧٨٤٦")
            
            p.drawString(100, 270, "وقائع الدعوى:")
            p.drawString(100, 240, "تتعلق القضية بقرار إداري صادر من الجهة المختصة")
            
            p.drawString(100, 210, "الطلب:")
            p.drawString(100, 180, "إلغاء القرار الإداري والتعويض عن الأضرار")
            
            p.save()
            pdf_content = buffer.getvalue()
            buffer.close()
            
            return pdf_content
            
        except ImportError:
            # If reportlab is not available, create a minimal PDF manually
            logger.warning("reportlab not available, creating minimal PDF")
            return self._create_minimal_pdf()
    
    def _create_minimal_pdf(self) -> bytes:
        """Create a minimal PDF file manually."""
        # This is a very basic PDF structure
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Sample Document) Tj\nET\nendstream\nendobj\n\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000204 00000 n\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n297\n%%EOF'
        return pdf_content
    
    async def test_text_processor(self) -> Dict[str, Any]:
        """Test the text processor component."""
        logger.info("🧠 Testing Text Processor")
        
        try:
            processor = TextProcessor()
            
            # Test with sample legal text
            sample_text = """
            صحيفة الدعوى
            
            بيانات صحيفة الدعوى:
            رقم الطلب: ١٣٨٣٩٥١
            التاريخ: ١٤٤٤/٠٣/١٩
            اسم المدعي: عبير احمد سعيد العمودي
            اسم المدعى عليه: أمانة منطقة الرياض
            رقم الجوال: ٠٥٤٨٠٠٦٧٠٠
            البريد الإلكتروني: maabeer@gmail.com
            
            معلومات المحكمة:
            المحكمة: المحكمة الإدارية بالرياض
            نوع الدعوى: دعوى إدارية
            موضوع الدعوى: طلب إلغاء قرار إداري
            """
            
            # Extract structured data
            structured_data = await processor.extract_structured_data(sample_text)
            
            # Test text sections
            sections = processor.extract_text_sections(sample_text)
            
            result = {
                "status": "success",
                "extracted_fields": len(structured_data),
                "field_names": list(structured_data.keys()),
                "sections_count": len(sections),
                "sample_fields": {
                    "case_number": structured_data.get("case_number"),
                    "plaintiff_name": structured_data.get("plaintiff_name"),
                    "defendant_name": structured_data.get("defendant_name"),
                    "court_name": structured_data.get("court_name")
                }
            }
            
            logger.info(f"✅ Text Processor: Extracted {len(structured_data)} fields")
            return result
            
        except Exception as e:
            logger.error(f"❌ Text Processor failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_openai_refiner(self) -> Dict[str, Any]:
        """Test the OpenAI refiner component."""
        logger.info("🤖 Testing OpenAI Refiner")
        
        try:
            refiner = OpenAIRefiner()
            
            # Test with sample data
            sample_text = "صحيفة دعوى تحتوي على معلومات المدعي والمدعى عليه"
            sample_claim = ClaimInfo(
                case_number="1383951",
                plaintiff_name="عبير احمد سعيد العمودي",
                defendant_name="أمانة منطقة الرياض",
                court_name="المحكمة الإدارية بالرياض",
                case_type="دعوى إدارية",
                case_subject="طلب إلغاء قرار إداري"
            )
            
            # Test refinement
            refined_response = await refiner.refine_claim_extraction(sample_text, sample_claim)
            
            # Test legal summary
            legal_summary = await refiner.generate_legal_summary(sample_claim)
            
            # Test enhanced analysis
            enhanced_analysis = await refiner.enhance_claim_analysis(sample_claim)
            
            result = {
                "status": "success",
                "refined_response_length": len(refined_response),
                "legal_summary_length": len(legal_summary),
                "enhanced_analysis": enhanced_analysis,
                "openai_available": refiner.client is not None
            }
            
            logger.info(f"✅ OpenAI Refiner: Refined response length: {len(refined_response)}")
            return result
            
        except Exception as e:
            logger.error(f"❌ OpenAI Refiner failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_storage_manager(self) -> Dict[str, Any]:
        """Test the storage manager component."""
        logger.info("📁 Testing Storage Manager")
        
        try:
            storage = StorageManager()
            
            # Test storage info
            storage_info = storage.get_storage_info()
            
            # Test file upload (mock)
            sample_content = b"test file content"
            mock_url = await storage.upload_file(
                file_content=sample_content,
                filename="test_claim.pdf",
                conversation_id="test_conversation"
            )
            
            # Test file metadata
            metadata = await storage.get_file_metadata(mock_url)
            
            # Test file listing
            files = await storage.list_files(conversation_id="test_conversation")
            
            result = {
                "status": "success",
                "storage_available": storage.is_storage_available(),
                "storage_info": storage_info,
                "mock_url": mock_url,
                "metadata": metadata,
                "files_count": len(files)
            }
            
            logger.info(f"✅ Storage Manager: Storage available: {storage.is_storage_available()}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Storage Manager failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_validator(self) -> Dict[str, Any]:
        """Test the claim validator component."""
        logger.info("✅ Testing Claim Validator")
        
        try:
            validator = ClaimValidator()
            
            # Test with valid claim
            valid_claim = ClaimInfo(
                case_number="1383951",
                plaintiff_name="عبير احمد سعيد العمودي",
                defendant_name="أمانة منطقة الرياض",
                court_name="المحكمة الإدارية بالرياض",
                case_type="دعوى إدارية",
                case_subject="طلب إلغاء قرار إداري",
                plaintiff_mobile="0548006700",
                plaintiff_email="maabeer@gmail.com",
                filing_date="2024/03/19"
            )
            
            # Test validation
            validation_result = await validator.validate_claim(valid_claim)
            
            # Test validation summary
            summary = validator.get_validation_summary(validation_result)
            
            # Test with invalid claim
            invalid_claim = ClaimInfo(
                case_number="",
                plaintiff_name="",
                defendant_name="",
                court_name="",
                case_type="",
                case_subject=""
            )
            
            invalid_result = await validator.validate_claim(invalid_claim)
            
            result = {
                "status": "success",
                "valid_claim_score": validation_result.score,
                "valid_claim_is_valid": validation_result.is_valid,
                "valid_claim_errors": len(validation_result.errors),
                "valid_claim_warnings": len(validation_result.warnings),
                "invalid_claim_score": invalid_result.score,
                "invalid_claim_is_valid": invalid_result.is_valid,
                "validation_summary": summary
            }
            
            logger.info(f"✅ Claim Validator: Valid claim score: {validation_result.score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Claim Validator failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_complete_extraction(self) -> Dict[str, Any]:
        """Test the complete claim extraction service."""
        logger.info("🚀 Testing Complete Claim Extraction")
        
        try:
            extractor = ClaimExtractorService()
            
            # Create sample PDF content
            pdf_content = self._create_sample_pdf_content()
            
            # Test complete extraction
            result = await extractor.extract_claim_from_pdf(
                file_content=pdf_content,
                filename="test_claim.pdf",
                conversation_id="test_conversation"
            )
            
            # Analyze results
            analysis = {
                "status": "success",
                "processing_id": result.processing_id,
                "extraction_status": result.status.value,
                "processing_time": result.processing_time,
                "file_url": result.file_url,
                "raw_text_length": len(result.raw_text) if result.raw_text else 0,
                "refined_response_length": len(result.refined_response) if result.refined_response else 0,
                "document_intelligence_confidence": result.document_intelligence_confidence,
                "openai_confidence": result.openai_confidence
            }
            
            # Add claim info if available
            if result.extracted_claim:
                analysis["claim_info"] = {
                    "case_number": result.extracted_claim.case_number,
                    "plaintiff_name": result.extracted_claim.plaintiff_name,
                    "defendant_name": result.extracted_claim.defendant_name,
                    "court_name": result.extracted_claim.court_name,
                    "is_valid": result.extracted_claim.is_valid,
                    "processing_confidence": result.extracted_claim.processing_confidence,
                    "validation_score": result.extracted_claim.get_validation_score()
                }
            
            logger.info(f"✅ Complete Extraction: Status: {result.status.value}, Time: {result.processing_time:.2f}s")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Complete Extraction failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all claim extractor tests."""
        logger.info("🧪 Starting Claim Extractor Test Suite")
        
        # Run individual component tests
        self.results["text_processor"] = await self.test_text_processor()
        self.results["openai_refiner"] = await self.test_openai_refiner()
        self.results["storage_manager"] = await self.test_storage_manager()
        self.results["validator"] = await self.test_validator()
        self.results["complete_extraction"] = await self.test_complete_extraction()
        
        # Calculate overall results
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result.get("status") == "success")
        failed_tests = total_tests - passed_tests
        
        # Calculate execution time
        execution_time = (datetime.now() - self.start_time).total_seconds()
        
        overall_result = {
            "test_suite": "Claim Extractor Module",
            "timestamp": datetime.now().isoformat(),
            "execution_time": execution_time,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "overall_status": "ALL_PASSED" if failed_tests == 0 else "SOME_FAILED",
            "results": self.results
        }
        
        # Log summary
        logger.info(f"📊 Test Summary:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   Passed: {passed_tests}")
        logger.info(f"   Failed: {failed_tests}")
        logger.info(f"   Success Rate: {overall_result['success_rate']:.1f}%")
        logger.info(f"   Execution Time: {execution_time:.2f}s")
        logger.info(f"   Overall Status: {overall_result['overall_status']}")
        
        return overall_result


async def main():
    """Main test execution function."""
    try:
        # Create tester
        tester = ClaimExtractorTester()
        
        # Run tests
        results = await tester.run_all_tests()
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"claim_extractor_test_results_{timestamp}.json"
        
        # Convert datetime objects to strings for JSON serialization
        serializable_results = results.copy()
        if "timestamp" in serializable_results:
            serializable_results["timestamp"] = serializable_results["timestamp"].isoformat()
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 Test results saved to: {results_file}")
        
        # Print detailed results
        print("\n" + "="*80)
        print("CLAIM EXTRACTOR TEST RESULTS")
        print("="*80)
        
        for test_name, result in results["results"].items():
            status_icon = "✅" if result.get("status") == "success" else "❌"
            print(f"{status_icon} {test_name.upper()}: {result.get('status', 'unknown')}")
            
            if result.get("status") == "error":
                print(f"   Error: {result.get('error', 'Unknown error')}")
        
        print("\n" + "="*80)
        print(f"OVERALL STATUS: {results['overall_status']}")
        print(f"SUCCESS RATE: {results['success_rate']:.1f}%")
        print(f"EXECUTION TIME: {results['execution_time']:.2f}s")
        print("="*80)
        
        return results
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    # Run the tests
    asyncio.run(main()) 