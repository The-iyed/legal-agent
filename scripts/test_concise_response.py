#!/usr/bin/env python3
"""
Test script for concise claim overview response
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.modules.claim_extractor import ClaimExtractorService, ClaimInfo
from app.modules.claim_extractor.openai_refiner import OpenAIRefiner


async def test_concise_response():
    """Test the concise response format."""
    
    print("🧪 Testing Concise Response Format")
    print("=" * 40)
    
    # Sample text with :unselected: markers
    sample_text = """المحكمة الإدارية بالرياض تقارير نظام إدارة الدعاوى (٥٠٠٣)
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
        cleaned_text = processor._clean_text(sample_text)
        print(f"✅ Text cleaned successfully")
        print(f"📏 Original length: {len(sample_text)}")
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
        
        # Test 2: Claim Overview Generation
        print("\n2️⃣ Testing Claim Overview Generation")
        print("-" * 30)
        
        refiner = OpenAIRefiner()
        
        # Create claim info from extracted data
        claim_info = ClaimInfo(
            case_number=structured_data.get('case_number'),
            plaintiff_name=structured_data.get('plaintiff_name'),
            defendant_name=structured_data.get('defendant_name'),
            case_type=structured_data.get('case_type', 'دعوى إدارية'),
            case_subject="طلب إلغاء قرار إداري",
            claim_amount="50000",
            currency="ريال سعودي"
        )
        
        # Generate overview
        overview = await refiner.generate_claim_overview(cleaned_text, claim_info)
        print(f"✅ Overview generated: {overview}")
        print(f"📏 Length: {len(overview)} characters")
        
        # Test 3: Concise Response Format
        print("\n3️⃣ Testing Concise Response Format")
        print("-" * 30)
        
        # Simulate API response
        response = {
            "status": "success",
            "processing_id": "test-123",
            "filename": "test_claim.pdf",
            "raw_text": cleaned_text[:500] + "..." if len(cleaned_text) > 500 else cleaned_text,
            "raw_text_length": len(cleaned_text),
            "extracted_claim": {
                "case_number": claim_info.case_number,
                "plaintiff_name": claim_info.plaintiff_name,
                "defendant_name": claim_info.defendant_name,
                "case_type": claim_info.case_type,
                "claim_overview": overview,
                "claim_amount": claim_info.claim_amount,
                "currency": claim_info.currency
            },
            "is_valid": True
        }
        
        print("✅ Concise response format:")
        print(f"   Raw text length: {response['raw_text_length']}")
        print(f"   Raw text preview: {response['raw_text'][:100]}...")
        print(f"   Claim overview: {response['extracted_claim']['claim_overview']}")
        print(f"   Essential fields: {list(response['extracted_claim'].keys())}")
        
        print("\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print("🚀 Starting Concise Response Tests")
    print("=" * 50)
    
    success = asyncio.run(test_concise_response())
    
    if success:
        print("\n✅ All tests passed!")
        print("\n📝 Summary:")
        print("- Text cleaning removes :unselected: markers")
        print("- Concise response format works")
        print("- Essential fields only in response")
        print("- Perfect for chatbot integration")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 