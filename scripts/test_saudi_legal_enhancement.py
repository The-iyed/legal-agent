#!/usr/bin/env python3
"""
Test Script for Enhanced Saudi Legal Document Processing

This script tests the enhanced claim extractor with Saudi legal document patterns
and validates the improved document intelligence processing.
"""

import asyncio
import json
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.modules.claim_extractor.service import ClaimExtractorService
from app.modules.claim_extractor.text_processor import TextProcessor
from app.modules.claim_extractor.models import ClaimInfo, ProcessingStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SaudiLegalDocumentTester:
    """Test class for Saudi legal document processing."""
    
    def __init__(self):
        self.claim_extractor = ClaimExtractorService()
        self.text_processor = TextProcessor()
    
    def _create_saudi_legal_pdf_content(self) -> bytes:
        """Create sample Saudi legal document PDF content."""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from io import BytesIO
            
            # Create PDF buffer
            buffer = BytesIO()
            
            # Create PDF
            p = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            
            # Set font (using default for now)
            p.setFont("Helvetica", 12)
            
            # Header
            p.drawString(50, height - 50, "المملكة العربية السعودية")
            p.drawString(50, height - 70, "ديوان المظالم")
            p.drawString(50, height - 90, "المحكمة الإدارية بالرياض")
            p.drawString(50, height - 110, "تقارير نظام إدارة الدعاوى (5003)")
            
            # Document metadata
            p.drawString(50, height - 140, "الاصدار: 2")
            p.drawString(50, height - 160, "تاريخ الاصدار: 1439")
            p.drawString(50, height - 180, "الصفحة: 1 من 3")
            p.drawString(50, height - 200, "التاريخ: 1444/03/20")
            p.drawString(50, height - 220, "الكود المرجعي: 2317707")
            
            # Case statement data
            p.drawString(50, height - 260, "بيانات صحيفة الدعوى")
            p.drawString(50, height - 280, "مقدمة للمحكمة: المحكمة الإدارية بالرياض")
            p.drawString(50, height - 300, "رقم الطلب: 1383951")
            p.drawString(50, height - 320, "رقم قيد الدعوى: 2024/001")
            p.drawString(50, height - 340, "التاريخ: 1444/03/19")
            p.drawString(50, height - 360, "طلب جديد")
            
            # National address
            p.drawString(50, height - 390, "العنوان الوطني")
            p.drawString(50, height - 410, "□ الرياض")
            p.drawString(50, height - 430, "□ جدة")
            p.drawString(50, height - 450, "□ الدمام")
            p.drawString(50, height - 470, "□ أخرى")
            
            # Additional information
            p.drawString(50, height - 500, "معلومات اضافية")
            p.drawString(50, height - 520, "رقم القرار: 000003657846")
            p.drawString(50, height - 540, "تاريخ القرار: 1444/03/02")
            p.drawString(50, height - 560, "تاريخ العلم القرار: 1444/03/02")
            p.drawString(50, height - 580, "رقم التظلم: 3805482")
            p.drawString(50, height - 600, "تاريخ التظلم: 1444/03/13")
            p.drawString(50, height - 620, "اطلب الغاء المخالف رقم: 10000003657846")
            
            # Requests in case
            p.drawString(50, height - 650, "الطلبات المقدمة في القضية")
            p.drawString(50, height - 670, "وصف الطلب:")
            p.drawString(50, height - 690, "طلب إلغاء القرار الإداري الصادر بتاريخ 1444/03/02")
            
            # Contact information
            p.drawString(50, height - 720, "بيانات التواصل")
            p.drawString(50, height - 740, "رقم الجوال الاساسي: 0548006700")
            p.drawString(50, height - 760, "رقم الجوال الاضافي: 0501234567")
            p.drawString(50, height - 780, "البريد الالكتروني: applicant@example.com")
            
            # Applicant information
            p.drawString(50, height - 810, "مقدم الطلب: عبير احمد سعيد العمودي")
            
            p.save()
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error creating Saudi legal PDF: {e}")
            # Fallback to simple text content
            return b"Sample Saudi Legal Document Content"
    
    async def test_text_processor_enhancements(self):
        """Test enhanced text processor with Saudi legal patterns."""
        logger.info("Testing enhanced text processor...")
        
        try:
            # Create sample text content
            sample_text = """
            المملكة العربية السعودية
            ديوان المظالم
            المحكمة الإدارية بالرياض
            تقارير نظام إدارة الدعاوى (5003)
            
            بيانات صحيفة الدعوى
            مقدمة للمحكمة: المحكمة الإدارية بالرياض
            رقم الطلب: 1383951
            رقم قيد الدعوى: 2024/001
            التاريخ: 1444/03/19
            طلب جديد
            
            العنوان الوطني
            □ الرياض □ جدة □ الدمام □ أخرى
            
            معلومات اضافية
            رقم القرار: 000003657846
            تاريخ القرار: 1444/03/02
            تاريخ العلم القرار: 1444/03/02
            رقم التظلم: 3805482
            تاريخ التظلم: 1444/03/13
            اطلب الغاء المخالف رقم: 10000003657846
            
            الطلبات المقدمة في القضية
            وصف الطلب: طلب إلغاء القرار الإداري الصادر بتاريخ 1444/03/02
            
            بيانات التواصل
            رقم الجوال الاساسي: 0548006700
            رقم الجوال الاضافي: 0501234567
            البريد الالكتروني: applicant@example.com
            
            مقدم الطلب: عبير احمد سعيد العمودي
            
            الكود المرجعي: 2317707
            """
            
            # Test structured data extraction
            extracted_data = await self.text_processor.extract_structured_data(sample_text)
            
            logger.info("Extracted structured data:")
            for field, value in extracted_data.items():
                logger.info(f"  {field}: {value}")
            
            # Test Saudi legal sections extraction
            sections = self.text_processor.extract_saudi_legal_sections(sample_text)
            
            logger.info("Extracted Saudi legal sections:")
            for section, content in sections.items():
                if content.strip():
                    logger.info(f"  {section}: {len(content)} characters")
            
            # Validate key fields
            expected_fields = [
                'request_number', 'case_registration_number', 'decision_date',
                'appeal_date', 'applicant_name', 'primary_mobile', 'reference_code'
            ]
            
            missing_fields = []
            for field in expected_fields:
                if field not in extracted_data or not extracted_data[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                logger.warning(f"Missing expected fields: {missing_fields}")
            else:
                logger.info("✅ All expected Saudi legal fields extracted successfully")
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error testing text processor enhancements: {e}")
            return {}
    
    async def test_complete_extraction_pipeline(self):
        """Test the complete extraction pipeline with Saudi legal documents."""
        logger.info("Testing complete extraction pipeline...")
        
        try:
            # Create sample PDF content
            pdf_content = self._create_saudi_legal_pdf_content()
            
            # Test complete extraction
            result = await self.claim_extractor.extract_claim_from_pdf(
                file_content=pdf_content,
                filename="saudi_legal_test.pdf",
                conversation_id="test_conversation_123"
            )
            
            logger.info(f"Extraction completed with status: {result.status}")
            logger.info(f"Processing time: {result.processing_time:.2f} seconds")
            
            if result.extracted_claim:
                logger.info("Extracted claim information:")
                claim_data = result.extracted_claim.dict()
                for field, value in claim_data.items():
                    if value:
                        logger.info(f"  {field}: {value}")
                
                # Check Saudi-specific fields
                saudi_fields = [
                    'request_number', 'case_registration_number', 'decision_date',
                    'appeal_date', 'applicant_name', 'primary_mobile', 'reference_code'
                ]
                
                saudi_extracted = sum(1 for field in saudi_fields 
                                    if getattr(result.extracted_claim, field))
                
                logger.info(f"Saudi-specific fields extracted: {saudi_extracted}/{len(saudi_fields)}")
                
                if saudi_extracted >= 3:
                    logger.info("✅ Saudi legal document processing working well")
                else:
                    logger.warning("⚠️ Limited Saudi-specific field extraction")
            
            if result.refined_response:
                logger.info("Refined response generated successfully")
                logger.info(f"Response length: {len(result.refined_response)} characters")
            
            return result
            
        except Exception as e:
            logger.error(f"Error testing complete extraction pipeline: {e}")
            return None
    
    async def test_document_intelligence_optimization(self):
        """Test the optimized document intelligence processing."""
        logger.info("Testing document intelligence optimization...")
        
        try:
            # Create sample PDF content
            pdf_content = self._create_saudi_legal_pdf_content()
            
            # Test with layout model (primary for structured forms)
            from app.modules.document_processor.enhanced_document_intelligence import EnhancedDocumentIntelligenceService, DocumentModel
            
            doc_intelligence = EnhancedDocumentIntelligenceService()
            
            # Test layout model
            layout_result = await doc_intelligence.analyze_document(
                file_content=pdf_content,
                model=DocumentModel.LAYOUT
            )
            
            logger.info(f"Layout model extracted {len(layout_result.extracted_text)} characters")
            logger.info(f"Layout confidence: {layout_result.confidence_score}")
            
            # Test document model
            doc_result = await doc_intelligence.analyze_document(
                file_content=pdf_content,
                model=DocumentModel.DOCUMENT
            )
            
            logger.info(f"Document model extracted {len(doc_result.extracted_text)} characters")
            logger.info(f"Document confidence: {doc_result.confidence_score}")
            
            # Compare results
            if len(layout_result.extracted_text) > len(doc_result.extracted_text):
                logger.info("✅ Layout model provided more comprehensive extraction")
            else:
                logger.info("⚠️ Document model provided more comprehensive extraction")
            
            return {
                "layout_result": layout_result,
                "document_result": doc_result
            }
            
        except Exception as e:
            logger.error(f"Error testing document intelligence optimization: {e}")
            return None
    
    async def run_all_tests(self):
        """Run all enhancement tests."""
        logger.info("🚀 Starting Saudi Legal Document Enhancement Tests")
        logger.info("=" * 60)
        
        results = {}
        
        # Test 1: Text processor enhancements
        logger.info("\n📝 Test 1: Text Processor Enhancements")
        results['text_processor'] = await self.test_text_processor_enhancements()
        
        # Test 2: Document intelligence optimization
        logger.info("\n🔍 Test 2: Document Intelligence Optimization")
        results['document_intelligence'] = await self.test_document_intelligence_optimization()
        
        # Test 3: Complete extraction pipeline
        logger.info("\n🔄 Test 3: Complete Extraction Pipeline")
        results['complete_pipeline'] = await self.test_complete_extraction_pipeline()
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 Test Summary")
        logger.info("=" * 60)
        
        if results['text_processor']:
            logger.info("✅ Text processor enhancements: PASSED")
        else:
            logger.error("❌ Text processor enhancements: FAILED")
        
        if results['document_intelligence']:
            logger.info("✅ Document intelligence optimization: PASSED")
        else:
            logger.error("❌ Document intelligence optimization: FAILED")
        
        if results['complete_pipeline']:
            logger.info("✅ Complete extraction pipeline: PASSED")
        else:
            logger.error("❌ Complete extraction pipeline: FAILED")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"test_logs/saudi_legal_enhancement_results_{timestamp}.json"
        
        os.makedirs("test_logs", exist_ok=True)
        
        # Convert results to serializable format
        serializable_results = {}
        for test_name, result in results.items():
            if hasattr(result, 'dict'):
                serializable_results[test_name] = result.dict()
            elif isinstance(result, dict):
                serializable_results[test_name] = result
            else:
                serializable_results[test_name] = str(result)
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📄 Test results saved to: {results_file}")
        
        return results


async def main():
    """Main test function."""
    tester = SaudiLegalDocumentTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 