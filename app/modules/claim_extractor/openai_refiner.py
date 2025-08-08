"""
OpenAI Refiner for Claim Extraction

This module uses Azure OpenAI to refine and enhance extracted claim information,
providing better structured responses and additional insights.
"""

import logging
import json
from typing import Optional, Dict, Any
from openai import AzureOpenAI

from app.core.config.settings import get_settings
from .models import ClaimInfo

logger = logging.getLogger(__name__)


class OpenAIRefiner:
    """Uses Azure OpenAI to refine extracted claim information."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Azure OpenAI client."""
        try:
            if (self.settings.AZURE_OPENAI_ENDPOINT and 
                self.settings.AZURE_OPENAI_API_KEY):
                deployment_name = getattr(self.settings, 'AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o')
                api_version = getattr(self.settings, 'AZURE_OPENAI_API_VERSION', '2024-11-20')
                self.client = AzureOpenAI(
                    api_key=self.settings.AZURE_OPENAI_API_KEY,
                    api_version=api_version,
                    azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT
                )
                self.deployment_name = deployment_name
                logger.info(f"OpenAI Refiner initialized with deployment: {deployment_name} (API version: {api_version})")
            else:
                logger.warning("Azure OpenAI credentials not configured")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
    
    async def refine_claim_extraction(
        self, 
        raw_text: str, 
        extracted_claim: Optional[ClaimInfo] = None
    ) -> str:
        """
        Refine extracted claim information using Azure OpenAI.
        
        Args:
            raw_text: Raw text extracted from document
            extracted_claim: Previously extracted claim information
            
        Returns:
            Refined response in Arabic
        """
        try:
            if not self.client:
                logger.warning("OpenAI client not available, returning basic response")
                return self._generate_basic_response(raw_text, extracted_claim)
            
            logger.info("Refining claim extraction with OpenAI")
            
            # Prepare the prompt
            prompt = self._create_refinement_prompt(raw_text, extracted_claim)
            
            # Call OpenAI
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": """أنت مساعد قانوني متخصص في تحليل المستندات القانونية السعودية. 
                        مهمتك تحليل النص المستخرج من صحيفة دعوى وتقديم تحليل شامل ومفصل باللغة العربية.
                        
                        يجب أن يتضمن تحليلك:
                        1. ملخص شامل للمستند
                        2. تحليل المعلومات المستخرجة
                        3. تقييم اكتمال المعلومات
                        4. توصيات للخطوات التالية
                        5. ملاحظات حول جودة المستند
                        
                        استخدم لغة قانونية مهنية ومفهومة."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            refined_response = response.choices[0].message.content.strip()
            logger.info("OpenAI refinement completed successfully")
            
            return refined_response
            
        except Exception as e:
            logger.error(f"Error refining with OpenAI: {e}")
            return self._generate_basic_response(raw_text, extracted_claim)
    
    async def generate_claim_overview(self, raw_text: str, extracted_claim: Optional[ClaimInfo] = None) -> str:
        """Generate a concise, chatbot-friendly claim overview."""
        try:
            if not self.client:
                logger.warning("OpenAI client not available, returning basic overview")
                return self._generate_basic_overview(raw_text, extracted_claim)
            
            logger.info("Generating concise claim overview with OpenAI")
            
            prompt = f"""
            أنت محامي متخصص في القانون السعودي. قم بتحليل النص التالي وتقديم تحليل قانوني شامل ومفصل للدعوى:

            النص المستخرج:
            {raw_text[:2000]}

            المعلومات المستخرجة:
            {extracted_claim.model_dump() if extracted_claim else "لا توجد معلومات مستخرجة"}

            المطلوب:
            اكتب تحليلاً قانونياً شاملاً للدعوى في 5-6 أسطر باللغة العربية، بأسلوب قانوني مهني ومفصل.
            يجب أن يتضمن:

            1. **معلومات الدعوى الأساسية**: نوع الدعوى، رقم القضية، تاريخ رفع الدعوى
            2. **الأطراف المعنية**: المدعي والمدعى عليه مع تفاصيلهم
            3. **موضوع الدعوى**: السبب الرئيسي والوقائع الأساسية
            4. **الطلبات المقدمة**: ما يطلبه المدعي بالتفصيل
            5. **التقييم القانوني**: تحليل أولي لقوة المطالبة والمتطلبات القانونية
            6. **التوصيات**: الخطوات التالية المطلوبة

            اكتب التحليل بأسلوب قانوني مهني ومفصل، مع استخدام المصطلحات القانونية المناسبة.
            """
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": """أنت محامي متخصص في القانون السعودي مع خبرة 20 عاماً في المحاكم الإدارية والتجارية والمدنية.
                        مهمتك تقديم تحليلات قانونية شاملة ومفصلة للدعاوى القانونية.
                        استخدم لغة قانونية مهنية ومصطلحات قانونية دقيقة.
                        قدم تحليلاً مفصلاً في 5-6 أسطر يتضمن جميع الجوانب القانونية المهمة."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=800
            )
            
            overview = response.choices[0].message.content.strip()
            logger.info("Claim overview generated successfully")
            
            return overview
            
        except Exception as e:
            logger.error(f"Error generating claim overview: {e}")
            return self._generate_basic_overview(raw_text, extracted_claim)
    
    def _create_refinement_prompt(self, raw_text: str, extracted_claim: Optional[ClaimInfo]) -> str:
        """Create the prompt for OpenAI refinement."""
        prompt = f"""
        النص المستخرج من صحيفة الدعوى:
        
        {raw_text[:3000]}...
        
        """
        
        if extracted_claim:
            prompt += f"""
        المعلومات المستخرجة:
        
        معلومات أساسية:
        - رقم القضية: {extracted_claim.case_number or 'غير محدد'}
        - رقم الطلب: {extracted_claim.claim_number or 'غير محدد'}
        - تاريخ رفع الدعوى: {extracted_claim.filing_date or 'غير محدد'}
        
        معلومات المدعي:
        - الاسم: {extracted_claim.plaintiff_name or 'غير محدد'}
        - رقم الهوية: {extracted_claim.plaintiff_id or 'غير محدد'}
        - رقم الجوال: {extracted_claim.plaintiff_mobile or 'غير محدد'}
        - البريد الإلكتروني: {extracted_claim.plaintiff_email or 'غير محدد'}
        - العنوان: {extracted_claim.plaintiff_address or 'غير محدد'}
        
        معلومات المدعى عليه:
        - الاسم: {extracted_claim.defendant_name or 'غير محدد'}
        - النوع: {extracted_claim.defendant_type or 'غير محدد'}
        - رقم الهوية: {extracted_claim.defendant_id or 'غير محدد'}
        
        معلومات المحكمة:
        - اسم المحكمة: {extracted_claim.court_name or 'غير محدد'}
        - نوع المحكمة: {extracted_claim.court_type or 'غير محدد'}
        - موقع المحكمة: {extracted_claim.court_location or 'غير محدد'}
        
        تفاصيل القضية:
        - نوع الدعوى: {extracted_claim.case_type or 'غير محدد'}
        - موضوع الدعوى: {extracted_claim.case_subject or 'غير محدد'}
        - وقائع الدعوى: {extracted_claim.case_facts or 'غير محدد'}
        - طلبات الدعوى: {extracted_claim.case_requests or 'غير محدد'}
        
        معلومات إضافية:
        - رقم القرار: {extracted_claim.decision_number or 'غير محدد'}
        - رقم التظلم: {extracted_claim.appeal_number or 'غير محدد'}
        - رقم المخالفة: {extracted_claim.violation_number or 'غير محدد'}
        - مبلغ المطالبة: {extracted_claim.claim_amount or 'غير محدد'} {extracted_claim.currency or 'ريال سعودي'}
        
        جودة الاستخراج:
        - مستوى الثقة: {extracted_claim.processing_confidence or 0.0}
        - صحة المستند: {'صحيح' if extracted_claim.is_valid else 'غير صحيح'}
        """
        else:
            prompt += """
        لم يتم استخراج معلومات منظمة من النص.
        """
        
        prompt += """
        
        يرجى تحليل هذه المعلومات وتقديم:
        1. ملخص شامل للمستند
        2. تقييم اكتمال المعلومات المستخرجة
        3. تحديد أي معلومات مفقودة أو غير واضحة
        4. توصيات للخطوات التالية
        5. ملاحظات حول جودة المستند
        
        قدم الإجابة باللغة العربية وبأسلوب قانوني مهني.
        """
        
        return prompt
    
    def _generate_basic_overview(self, raw_text: str, extracted_claim: Optional[ClaimInfo]) -> str:
        """Generate a basic claim overview when OpenAI is not available."""
        try:
            if extracted_claim:
                # Create a concise overview in one or two sentences
                case_type = extracted_claim.case_type or "قانونية"
                
                # Clean up plaintiff name (take first part if too long)
                plaintiff = extracted_claim.plaintiff_name or "المدعي"
                if len(plaintiff) > 50:
                    plaintiff = plaintiff.split()[0] if plaintiff.split() else "المدعي"
                
                # Clean up defendant name (take first part if too long)
                defendant = extracted_claim.defendant_name or "المدعى عليه"
                if len(defendant) > 50:
                    defendant = defendant.split()[0] if defendant.split() else "المدعى عليه"
                
                # Determine case subject based on available information
                subject = extracted_claim.case_subject
                if not subject:
                    # Try to extract from raw text
                    if "مخالفة" in raw_text or "مخالف" in raw_text:
                        subject = "طلب إلغاء قرار إداري"
                    elif "تعويض" in raw_text:
                        subject = "طلب تعويض"
                    else:
                        subject = "طلب قانوني"
                
                amount = f" بمبلغ {extracted_claim.claim_amount} {extracted_claim.currency}" if extracted_claim.claim_amount else ""
                
                overview = f"دعوى {case_type} مقدمة من {plaintiff} ضد {defendant}، {subject}{amount}."
            else:
                overview = "تم استخراج نص من صحيفة دعوى، يرجى مراجعة المحتوى للتفاصيل."
            
            return overview.strip()
            
        except Exception as e:
            logger.error(f"Error generating basic overview: {e}")
            return "حدث خطأ في إنشاء ملخص الدعوى. يرجى المحاولة مرة أخرى."

    def _generate_basic_response(self, raw_text: str, extracted_claim: Optional[ClaimInfo]) -> str:
        """Generate a basic response when OpenAI is not available."""
        try:
            response = "## تحليل صحيفة الدعوى\n\n"
            
            if extracted_claim:
                response += f"""
### ملخص المستند
تم استخراج معلومات من صحيفة دعوى تحتوي على {extracted_claim.total_pages or 1} صفحة.

### المعلومات المستخرجة
- **رقم القضية**: {extracted_claim.case_number or 'غير محدد'}
- **اسم المدعي**: {extracted_claim.plaintiff_name or 'غير محدد'}
- **اسم المدعى عليه**: {extracted_claim.defendant_name or 'غير محدد'}
- **المحكمة**: {extracted_claim.court_name or 'غير محدد'}
- **نوع الدعوى**: {extracted_claim.case_type or 'غير محدد'}

### تقييم اكتمال المعلومات
مستوى اكتمال المعلومات: {extracted_claim.get_validation_score() * 100:.1f}%

### النص المستخرج
{raw_text[:500]}...

### ملاحظات
- تم استخراج المعلومات باستخدام تقنيات الذكاء الاصطناعي
- يوصى بمراجعة المعلومات المستخرجة للتأكد من دقتها
- قد تحتاج بعض المعلومات إلى تحديث أو تصحيح يدوي
                """
            else:
                response += f"""
### ملاحظة
تم استخراج النص من المستند ولكن لم يتم تحليل المعلومات بشكل منظم.

### النص المستخرج
{raw_text[:500]}...

### توصية
يوصى بمراجعة النص يدوياً لاستخراج المعلومات المطلوبة.
                """
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating basic response: {e}")
            return "حدث خطأ في تحليل المستند. يرجى المحاولة مرة أخرى."
    
    async def enhance_claim_analysis(self, claim_info: ClaimInfo) -> Dict[str, Any]:
        """
        Enhance claim analysis with additional insights using OpenAI.
        
        Args:
            claim_info: Extracted claim information
            
        Returns:
            Enhanced analysis with additional insights
        """
        try:
            if not self.client:
                return {"enhancement": "OpenAI غير متاح", "insights": []}
            
            prompt = f"""
            تحليل متقدم لصحيفة الدعوى:
            
            معلومات الدعوى:
            - نوع الدعوى: {claim_info.case_type}
            - موضوع الدعوى: {claim_info.case_subject}
            - مبلغ المطالبة: {claim_info.claim_amount}
            - المحكمة: {claim_info.court_name}
            
            يرجى تقديم:
            1. تحليل قانوني للمطالبة
            2. تقييم قوة المطالبة
            3. المتطلبات القانونية المحتملة
            4. التوصيات للخطوات التالية
            
            قدم الإجابة باللغة العربية وبأسلوب قانوني مهني.
            """
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "أنت محامي متخصص في القانون السعودي. قدم تحليلاً قانونياً دقيقاً ومهنياً."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            enhanced_analysis = response.choices[0].message.content.strip()
            
            return {
                "enhancement": enhanced_analysis,
                "insights": [
                    "تحليل قانوني شامل",
                    "تقييم قوة المطالبة",
                    "متطلبات قانونية",
                    "توصيات للخطوات التالية"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error enhancing claim analysis: {e}")
            return {
                "enhancement": "فشل في التحليل المتقدم",
                "insights": []
            }
    
    async def generate_legal_summary(self, claim_info: ClaimInfo) -> str:
        """
        Generate a legal summary of the claim.
        
        Args:
            claim_info: Extracted claim information
            
        Returns:
            Legal summary in Arabic
        """
        try:
            if not self.client:
                return "ملخص قانوني غير متاح"
            
            prompt = f"""
            اكتب ملخصاً قانونياً مختصراً لصحيفة الدعوى التالية:
            
            المدعي: {claim_info.plaintiff_name}
            المدعى عليه: {claim_info.defendant_name}
            نوع الدعوى: {claim_info.case_type}
            موضوع الدعوى: {claim_info.case_subject}
            المحكمة: {claim_info.court_name}
            مبلغ المطالبة: {claim_info.claim_amount} {claim_info.currency}
            
            قدم ملخصاً قانونياً واضحاً ومختصراً باللغة العربية.
            """
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "أنت محامي متخصص. اكتب ملخصاً قانونياً دقيقاً ومختصراً."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating legal summary: {e}")
            return "فشل في إنشاء الملخص القانوني" 