#!/usr/bin/env python3
"""
Enhanced Document Intelligence Test Script

This script tests the enhanced document intelligence capabilities including:
- Multiple model analysis
- Legal document field extraction
- Document summarization
- Health checks
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import json
from pathlib import Path
import tempfile

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.modules.document_processor.enhanced_document_intelligence import (
    EnhancedDocumentIntelligenceService,
    DocumentModel
)
from app.core.config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentIntelligenceTester:
    """Test enhanced document intelligence capabilities."""
    
    def __init__(self):
        self.settings = get_settings()
        self.service = EnhancedDocumentIntelligenceService()
        self.test_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "service_health": {},
            "model_tests": {},
            "legal_extraction": {},
            "summary_tests": {},
            "overall_status": "unknown"
        }
    
    def test_service_health(self) -> Dict[str, Any]:
        """Test if the Document Intelligence service is healthy."""
        logger.info("🏥 Testing Document Intelligence service health...")
        
        try:
            is_available = self.service.client is not None
            endpoint_configured = bool(self.settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT)
            api_key_configured = bool(self.settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY)
            
            health_status = {
                "status": "healthy" if is_available else "unavailable",
                "client_initialized": is_available,
                "endpoint_configured": endpoint_configured,
                "api_key_configured": api_key_configured,
                "all_configured": endpoint_configured and api_key_configured
            }
            
            if not is_available:
                health_status["message"] = "Document Intelligence client not initialized"
                health_status["recommendations"] = [
                    "Check AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT environment variable",
                    "Check AZURE_DOCUMENT_INTELLIGENCE_API_KEY environment variable",
                    "Verify Azure Document Intelligence service is running"
                ]
            
            logger.info(f"✅ Service health: {health_status['status']}")
            return health_status
            
        except Exception as e:
            logger.error(f"❌ Service health test failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _create_sample_pdf_content(self) -> bytes:
        """Create a simple PDF file for testing."""
        try:
            # Try to use reportlab to create a PDF
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from io import BytesIO
            
            buffer = BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            
            # Add some text content
            p.drawString(100, 750, "Sample Document")
            p.drawString(100, 720, "This is a test document for Document Intelligence testing.")
            p.drawString(100, 690, "Document Information:")
            p.drawString(100, 660, "Title: Test Document")
            p.drawString(100, 630, "Date: 2024/01/01")
            p.drawString(100, 600, "Author: Test User")
            p.drawString(100, 570, "Department: Testing Department")
            
            p.drawString(100, 540, "Content:")
            p.drawString(100, 510, "This document contains various types of information including:")
            p.drawString(100, 480, "- Text content")
            p.drawString(100, 450, "- Key-value pairs")
            p.drawString(100, 420, "- Structured data")
            
            p.drawString(100, 390, "Contact Information:")
            p.drawString(100, 360, "Email: test@example.com")
            p.drawString(100, 330, "Phone: +1234567890")
            p.drawString(100, 300, "Address: 123 Test Street, Test City")
            
            p.drawString(100, 270, "Additional Notes:")
            p.drawString(100, 240, "This is a comprehensive test document designed to validate")
            p.drawString(100, 210, "the enhanced document intelligence capabilities.")
            
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
        pdf_content = b'''%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Sample Document) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000204 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
297
%%EOF'''
        return pdf_content
    
    def _create_legal_pdf_content(self) -> bytes:
        """Create a PDF with legal document content for testing."""
        try:
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
            logger.warning("reportlab not available, creating minimal legal PDF")
            return self._create_minimal_pdf()
    
    async def test_single_model_analysis(self, model: DocumentModel) -> Dict[str, Any]:
        """Test analysis with a single model."""
        logger.info(f"📄 Testing model: {model.value}")
        
        try:
            # Create sample PDF content
            file_content = self._create_sample_pdf_content()
            
            # Analyze document
            result = await self.service.analyze_document(file_content, model)
            
            test_result = {
                "status": "success",
                "model_used": result.model_used,
                "confidence": result.confidence,
                "pages": result.pages,
                "processing_time": result.processing_time,
                "languages": result.languages,
                "extracted_text_length": len(result.extracted_text),
                "key_value_pairs_count": len(result.key_value_pairs),
                "form_fields_count": len(result.form_fields),
                "tables_count": len(result.tables),
                "images_count": len(result.images),
                "paragraphs_count": len(result.paragraphs),
                "lines_count": len(result.lines),
                "words_count": len(result.words)
            }
            
            logger.info(f"✅ Model {model.value} analysis successful")
            return test_result
            
        except Exception as e:
            logger.error(f"❌ Model {model.value} test failed: {e}")
            return {
                "status": "error",
                "model": model.value,
                "error": str(e)
            }
    
    async def test_multiple_models_analysis(self) -> Dict[str, Any]:
        """Test analysis with multiple models."""
        logger.info("🔄 Testing multiple models analysis...")
        
        try:
            # Create sample PDF content
            file_content = self._create_sample_pdf_content()
            
            # Test with common models
            models = [
                DocumentModel.DOCUMENT,
                DocumentModel.LAYOUT,
                DocumentModel.READ
            ]
            
            results = await self.service.analyze_with_multiple_models(file_content, models)
            
            test_result = {
                "status": "success",
                "models_used": list(results.keys()),
                "total_models": len(results),
                "results": {}
            }
            
            for model_name, result in results.items():
                test_result["results"][model_name] = {
                    "confidence": result.confidence,
                    "pages": result.pages,
                    "processing_time": result.processing_time,
                    "languages": result.languages,
                    "extracted_text_length": len(result.extracted_text),
                    "key_value_pairs_count": len(result.key_value_pairs),
                    "form_fields_count": len(result.form_fields),
                    "tables_count": len(result.tables),
                    "images_count": len(result.images)
                }
            
            logger.info(f"✅ Multiple models analysis successful with {len(results)} models")
            return test_result
            
        except Exception as e:
            logger.error(f"❌ Multiple models test failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_legal_document_extraction(self) -> Dict[str, Any]:
        """Test legal document field extraction."""
        logger.info("⚖️ Testing legal document field extraction...")
        
        try:
            # Create sample legal PDF content
            file_content = self._create_legal_pdf_content()
            
            # Extract legal fields
            result = await self.service.extract_legal_document_fields(file_content)
            
            test_result = {
                "status": "success",
                "document_type": result["document_type"],
                "confidence": result["confidence"],
                "pages": result["pages"],
                "processing_time": result["processing_time"],
                "extracted_fields": result["extracted_fields"],
                "raw_text_length": len(result["raw_text"]),
                "key_value_pairs_count": len(result["key_value_pairs"]),
                "form_fields_count": len(result["form_fields"])
            }
            
            # Check if key legal fields were extracted
            extracted_fields = result["extracted_fields"]
            key_fields = ["case_number", "plaintiff", "defendant", "court", "case_type"]
            extracted_count = sum(1 for field in key_fields if extracted_fields.get(field) and extracted_fields[field] != "غير مذكور")
            
            test_result["key_fields_extracted"] = extracted_count
            test_result["key_fields_total"] = len(key_fields)
            test_result["extraction_rate"] = f"{(extracted_count/len(key_fields)*100):.1f}%"
            
            logger.info(f"✅ Legal document extraction successful - {test_result['extraction_rate']} key fields extracted")
            return test_result
            
        except Exception as e:
            logger.error(f"❌ Legal document extraction test failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def test_document_summary(self) -> Dict[str, Any]:
        """Test document summary generation."""
        logger.info("📋 Testing document summary generation...")
        
        try:
            # Create sample PDF content
            file_content = self._create_sample_pdf_content()
            
            # Get document summary
            summary = await self.service.get_document_summary(file_content)
            
            test_result = {
                "status": "success",
                "document_type": summary["document_type"],
                "confidence": summary["confidence"],
                "pages": summary["pages"],
                "languages": summary["languages"],
                "has_tables": summary["has_tables"],
                "has_images": summary["has_images"],
                "key_value_pairs_count": summary["key_value_pairs_count"],
                "form_fields_count": summary["form_fields_count"],
                "text_length": summary["text_length"],
                "processing_time": summary["processing_time"],
                "extracted_text_preview_length": len(summary["extracted_text_preview"])
            }
            
            logger.info(f"✅ Document summary generation successful - Type: {summary['document_type']}")
            return test_result
            
        except Exception as e:
            logger.error(f"❌ Document summary test failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all document intelligence tests."""
        logger.info("🚀 Starting Enhanced Document Intelligence Test Suite...")
        logger.info("=" * 70)
        
        # Test service health
        health_test = self.test_service_health()
        self.test_results["service_health"] = health_test
        
        if health_test.get("status") != "healthy":
            logger.warning("⚠️ Service health check failed, some tests may not work")
        
        # Test individual models
        model_tests = {}
        for model in [DocumentModel.DOCUMENT, DocumentModel.LAYOUT, DocumentModel.READ]:
            test_result = await self.test_single_model_analysis(model)
            model_tests[model.value] = test_result
        
        self.test_results["model_tests"] = model_tests
        
        # Test multiple models analysis
        multi_model_test = await self.test_multiple_models_analysis()
        self.test_results["multiple_models"] = multi_model_test
        
        # Test legal document extraction
        legal_test = await self.test_legal_document_extraction()
        self.test_results["legal_extraction"] = legal_test
        
        # Test document summary
        summary_test = await self.test_document_summary()
        self.test_results["summary_tests"] = summary_test
        
        # Determine overall status
        all_tests = [health_test, multi_model_test, legal_test, summary_test]
        all_tests.extend(model_tests.values())
        
        success_count = sum(1 for test in all_tests if test.get("status") == "success")
        error_count = sum(1 for test in all_tests if test.get("status") == "error")
        
        if error_count == 0:
            self.test_results["overall_status"] = "all_passed"
        elif success_count > 0:
            self.test_results["overall_status"] = "partial_success"
        else:
            self.test_results["overall_status"] = "all_failed"
        
        self.test_results["summary"] = {
            "total_tests": len(all_tests),
            "passed": success_count,
            "failed": error_count,
            "success_rate": f"{(success_count/len(all_tests)*100):.1f}%"
        }
        
        return self.test_results
    
    def print_results(self, results: Dict[str, Any]):
        """Print test results in a formatted way."""
        logger.info("=" * 70)
        logger.info("📊 ENHANCED DOCUMENT INTELLIGENCE TEST RESULTS")
        logger.info("=" * 70)
        
        # Overall status
        status_emoji = {
            "all_passed": "✅",
            "partial_success": "⚠️",
            "all_failed": "❌"
        }
        
        overall_status = results.get("overall_status", "unknown")
        emoji = status_emoji.get(overall_status, "❓")
        logger.info(f"{emoji} Overall Status: {overall_status.upper()}")
        
        # Summary
        summary = results.get("summary", {})
        logger.info(f"📈 Success Rate: {summary.get('success_rate', '0%')}")
        logger.info(f"✅ Passed: {summary.get('passed', 0)}/{summary.get('total_tests', 0)}")
        logger.info(f"❌ Failed: {summary.get('failed', 0)}/{summary.get('total_tests', 0)}")
        
        logger.info("\n" + "=" * 70)
        logger.info("🔍 DETAILED RESULTS")
        logger.info("=" * 70)
        
        # Service health
        health_test = results.get("service_health", {})
        status_emoji = "✅" if health_test.get("status") == "healthy" else "❌"
        logger.info(f"\n{status_emoji} Service Health: {health_test.get('status', 'unknown')}")
        if health_test.get("message"):
            logger.info(f"  Message: {health_test['message']}")
        
        # Model tests
        model_tests = results.get("model_tests", {})
        logger.info(f"\n📄 Individual Model Tests: {len(model_tests)} models")
        for model_name, test_result in model_tests.items():
            status_emoji = "✅" if test_result.get("status") == "success" else "❌"
            logger.info(f"  {status_emoji} {model_name}: {test_result.get('status', 'unknown')}")
            if test_result.get("status") == "success":
                logger.info(f"    Confidence: {test_result.get('confidence', 0):.2f}")
                logger.info(f"    Processing Time: {test_result.get('processing_time', 0):.2f}s")
        
        # Multiple models
        multi_test = results.get("multiple_models", {})
        status_emoji = "✅" if multi_test.get("status") == "success" else "❌"
        logger.info(f"\n{status_emoji} Multiple Models Analysis: {multi_test.get('status', 'unknown')}")
        if multi_test.get("status") == "success":
            logger.info(f"  Models Used: {', '.join(multi_test.get('models_used', []))}")
            logger.info(f"  Total Models: {multi_test.get('total_models', 0)}")
        
        # Legal extraction
        legal_test = results.get("legal_extraction", {})
        status_emoji = "✅" if legal_test.get("status") == "success" else "❌"
        logger.info(f"\n{status_emoji} Legal Document Extraction: {legal_test.get('status', 'unknown')}")
        if legal_test.get("status") == "success":
            logger.info(f"  Extraction Rate: {legal_test.get('extraction_rate', '0%')}")
            logger.info(f"  Key Fields Extracted: {legal_test.get('key_fields_extracted', 0)}/{legal_test.get('key_fields_total', 0)}")
            logger.info(f"  Processing Time: {legal_test.get('processing_time', 0):.2f}s")
        
        # Document summary
        summary_test = results.get("summary_tests", {})
        status_emoji = "✅" if summary_test.get("status") == "success" else "❌"
        logger.info(f"\n{status_emoji} Document Summary: {summary_test.get('status', 'unknown')}")
        if summary_test.get("status") == "success":
            logger.info(f"  Document Type: {summary_test.get('document_type', 'unknown')}")
            logger.info(f"  Text Length: {summary_test.get('text_length', 0)} characters")
            logger.info(f"  Processing Time: {summary_test.get('processing_time', 0):.2f}s")
        
        logger.info("\n" + "=" * 70)
        logger.info("🎯 RECOMMENDATIONS")
        logger.info("=" * 70)
        
        # Provide recommendations based on results
        if results.get("overall_status") == "all_passed":
            logger.info("✅ All enhanced document intelligence features are working correctly!")
            logger.info("🚀 You can now use advanced document analysis capabilities.")
        elif results.get("overall_status") == "partial_success":
            logger.info("⚠️ Some features are working, but there are issues:")
            if health_test.get("status") != "healthy":
                logger.info("  - Fix Document Intelligence service configuration")
            if any(test.get("status") == "error" for test in model_tests.values()):
                logger.info("  - Some document analysis models are failing")
            if legal_test.get("status") != "success":
                logger.info("  - Legal document extraction needs attention")
            if summary_test.get("status") != "success":
                logger.info("  - Document summary generation needs attention")
        else:
            logger.info("❌ Multiple features are not working:")
            logger.info("  - Check Azure Document Intelligence configuration")
            logger.info("  - Verify environment variables")
            logger.info("  - Check network connectivity")
        
        logger.info("=" * 70)


def main():
    """Main function to run the enhanced document intelligence test suite."""
    try:
        tester = DocumentIntelligenceTester()
        results = asyncio.run(tester.run_all_tests())
        tester.print_results(results)
        
        # Save results to file
        output_file = f"enhanced_document_intelligence_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n📄 Detailed results saved to: {output_file}")
        
        # Exit with appropriate code
        if results.get("overall_status") == "all_passed":
            sys.exit(0)
        elif results.get("overall_status") == "partial_success":
            sys.exit(1)
        else:
            sys.exit(2)
            
    except Exception as e:
        logger.error(f"Enhanced document intelligence test suite failed with error: {str(e)}")
        sys.exit(3)


if __name__ == "__main__":
    main() 