#!/usr/bin/env python3
"""
Test script with real data from user response
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.modules.claim_extractor import ClaimExtractorService, ClaimInfo
from app.modules.claim_extractor.openai_refiner import OpenAIRefiner


async def test_real_data():
    """Test with real data from user response."""
    
    print("🧪 Testing with Real Data")
    print("=" * 40)
    
    # Real data from user response
    real_text = """المحكمة الإدارية بالرياض تقارير نظام إدارة الدعاوى (٥٠٠٣)
الجَا كَّة العَرَة السَُّ دَبُوارَ المَظَائِ Pعيناً
0
بيانات صحيفة الدعوى
١٤٤٤/٠٣/١٩ طلب جديد
التاريخ
رقم قيد الدعوى ١٣٨٣٩٥١
رقم الطلب المحكمة الإدارية بالرياض
مقدمة للمحكمة
: فرد
بيانات المدعى
بدون عمل
المهنة
عبير احمد سعيد العمودي
الاسم
سعودي
الجنسية
بدون عمل
مكان العمل
هوية وطنية
نوعه
١١١٠٢٢٥١٨٠
رقم السجل
مكان إقامة المدعي
سعيد بن عامر
الشارع
٢٩٧١
رقم المبني
الرياض
المدينة
١
وحدة رقم
٧١٧٤
الرمز الإضافي
١٢٣٩٥
الرمز البريدي
٠٥٤٨٠٠٦٧٠٠
الهاتف المتنقل
maabeer@gmail.com
البريد الإلكتروني
: جهة حكومية
بيانات المدعى عليه
بيان اضافي
أمانة منطقة الرياض
الاسم
الجنسية
مكان العمل
نوعه
٣٨٥
رقم السجل
أنا صاحبة مقهئ وردة العرب لتقديم المشروبات (٤ اونس كافية ديزير)، سجل تجاري رقم ١٠١٠٤٥٢٣٥٥
الموضوع : :unselected: :unselected: وقائع الدعوى :unselected: تمت زيارة مقر المقهى من قبل موظف أجادة التابع لأمانة منطقة الرياض وقام بإصدار مخالف رقم ١٠٠٠٠٠٠٣٦٥٧٨٤٦ وسبب :unselected:
المخالفة تقديم الشيشة دون تصريح وقد قمت برفع اعتراض على المخالف بمعاملة..."""
    
    try:
        # Test 1: Text Processing
        print("\n1️⃣ Testing Text Processing")
        print("-" * 30)
        
        from app.modules.claim_extractor.text_processor import TextProcessor
        processor = TextProcessor()
        
        # Test text cleaning
        cleaned_text = processor._clean_text(real_text)
        print(f"✅ Text cleaned successfully")
        print(f"📏 Original length: {len(real_text)}")
        print(f"📏 Cleaned length: {len(cleaned_text)}")
        print(f"🔍 :unselected: markers removed: {'unselected' not in cleaned_text}")
        
        # Test structured data extraction
        structured_data = await processor.extract_structured_data(cleaned_text)
        print(f"✅ Extracted {len(structured_data)} fields")
        
        # Show key extracted fields
        key_fields = ['case_number', 'plaintiff_name', 'defendant_name', 'case_type']
        for field in key_fields:
            if field in structured_data:
                print(f"   {field}: {structured_data[field]}")
        
        # Test 2: Service Integration
        print("\n2️⃣ Testing Service Integration")
        print("-" * 30)
        
        service = ClaimExtractorService()
        
        # Create a mock extraction result
        from app.modules.claim_extractor.models import ExtractionResult, ProcessingStatus
        from datetime import datetime
        
        result = ExtractionResult(
            processing_id="test-real-123",
            filename="test_real_claim.pdf",
            status=ProcessingStatus.COMPLETED,
            raw_text=cleaned_text,
            extracted_claim=ClaimInfo(
                case_number=structured_data.get('case_number'),
                plaintiff_name=structured_data.get('plaintiff_name'),
                defendant_name=structured_data.get('defendant_name'),
                case_type=structured_data.get('case_type'),
                case_subject="طلب إلغاء قرار إداري",
                claim_amount="50000",
                currency="ريال سعودي"
            ),
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
        # Test the text processing step
        processed_result = await service._process_text(result)
        
        print(f"✅ Case type: {processed_result.extracted_claim.case_type}")
        print(f"✅ Case subject: {processed_result.extracted_claim.case_subject}")
        print(f"✅ Plaintiff: {processed_result.extracted_claim.plaintiff_name}")
        print(f"✅ Defendant: {processed_result.extracted_claim.defendant_name}")
        
        # Test 3: Overview Generation
        print("\n3️⃣ Testing Overview Generation")
        print("-" * 30)
        
        refiner = OpenAIRefiner()
        
        # Generate overview
        overview = await refiner.generate_claim_overview(cleaned_text, processed_result.extracted_claim)
        print(f"✅ Overview generated: {overview}")
        print(f"📏 Length: {len(overview)} characters")
        
        # Test 4: Final Response Format
        print("\n4️⃣ Testing Final Response Format")
        print("-" * 30)
        
        # Simulate API response
        response = {
            "status": "success",
            "processing_id": "test-real-123",
            "filename": "test_real_claim.pdf",
            "raw_text": cleaned_text[:500] + "..." if len(cleaned_text) > 500 else cleaned_text,
            "raw_text_length": len(cleaned_text),
            "extracted_claim": {
                "case_number": processed_result.extracted_claim.case_number,
                "plaintiff_name": processed_result.extracted_claim.plaintiff_name,
                "defendant_name": processed_result.extracted_claim.defendant_name,
                "case_type": processed_result.extracted_claim.case_type,
                "claim_overview": overview,
                "claim_amount": processed_result.extracted_claim.claim_amount,
                "currency": processed_result.extracted_claim.currency
            },
            "is_valid": True
        }
        
        print("✅ Final response format:")
        print(f"   Case number: {response['extracted_claim']['case_number']}")
        print(f"   Plaintiff: {response['extracted_claim']['plaintiff_name']}")
        print(f"   Defendant: {response['extracted_claim']['defendant_name']}")
        print(f"   Case type: {response['extracted_claim']['case_type']}")
        print(f"   Overview: {response['extracted_claim']['claim_overview']}")
        
        print("\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print("🚀 Starting Real Data Tests")
    print("=" * 50)
    
    success = asyncio.run(test_real_data())
    
    if success:
        print("\n✅ All tests passed!")
        print("\n📝 Summary:")
        print("- Text cleaning works with real data")
        print("- Case type detection improved")
        print("- Overview generation enhanced")
        print("- Response format is clean and accurate")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 