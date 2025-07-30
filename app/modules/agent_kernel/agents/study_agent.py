from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
import logging
from ....core.config import settings, Settings

logger = logging.getLogger(__name__)

class StudyAgent(BaseAgent):
    """Agent for handling legislation-related queries using embedded data in prompts."""

    def __init__(self, settings: Settings = settings):
        super().__init__(settings)
        self._prompt_manager = None

    @property
    def prompt_manager(self):
        """Lazy load PromptManager to avoid circular imports."""
        if self._prompt_manager is None:
            from ...prompt_manager.manager import PromptManager
            self._prompt_manager = PromptManager()
        return self._prompt_manager

    async def execute(self, query: str, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        try:
            # Handle specific common queries with hardcoded responses for speed
            if any(phrase in query for phrase in ["ما هي التشريعات المتاحة", "التشريعات المتاحة", "اعرض التشريعات", "قائمة التشريعات"]):
                return await self._get_available_legislation_response(query)
            
            # Handle building materials queries
            if any(phrase in query for phrase in ["مواد البناء", "البناء", "المباني", "التشييد", "الإنشاء", "المختص في البناء", "المختص في مواد البناء"]):
                return await self._get_building_materials_response(query)
            
            # For all other queries, use the prompt with embedded data
            return await self._handle_prompt_based_query(query, prompt, context)
                
        except Exception as e:
            logger.error(f"Error in StudyAgent execution: {str(e)}", exc_info=True)
            return await self._get_error_response(query, str(e))

    async def _handle_prompt_based_query(self, query: str, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Handle queries using the prompt with embedded legislation data."""
        try:
            formatted_prompt = prompt.replace("{{$query}}", query)
            
            messages = [{"role": "system", "content": formatted_prompt}]
            
            completion = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=0.1,
                max_tokens=1500
            )
            
            response_content = completion.choices[0].message.content.strip()
            
            return {
                "response": {
                    "content": self._format_response(response_content),
                    "metadata": {
                        "agent_type": self.agent_type,
                        "last_query": query,
                        "source": "embedded_prompt_data"
                    }
                },
                "agent_type": self.agent_type,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error handling prompt-based query: {str(e)}", exc_info=True)
            return await self._get_error_response(query, str(e))

    async def _get_available_legislation_response(self, query: str) -> Dict[str, Any]:
        """Hardcoded response for available legislation queries."""
        logger.info("Returning hardcoded legislation list for speed")
        
        hardcoded_response = """## 📋 **قائمة التشريعات المتاحة** (26 تشريع)

### 🏗️ **نظام كود البناء السعودي** (5)
- نظام تطبيق كود البناء السعودي (م/43)
- اللائحة التنفيذية لنظام تطبيق كود البناء السعودي
- اللائحة التنفيذية لنظام تطبيق كود البناء السعودي - التعديل
- لائحة متطلبات تعيين جهات التفتيش والمفتشين
- لائحة تصنيف مخالفات كود البناء السعودي

### 📢 **تعاميم وزارية** (11)
- محضر اتفاق تحديد نسب البناء ومجالات الاستثمار - الأراضي والمباني الخاصة بوزارة البيئة والمياه والزراعة
- بشأن الموافقة على نظام الأجهزة والمستلزمات الطبية - مراقبة الهيئة العامة للغذاء والدواء
- صورة قرار مجلس الوزراء رقم (328) - الموافقة على السياسة الوطنية للسلامة والصحة المهنية
- بشأن تزويد وزارة الرياضة ببيان المنشآت الرياضية
- متابعة تطبيق الإجراءات الاحترازية - التدابير الوقائية لمنع تفشي فيروس كورونا
- ضم قطاع الأراضي بوكالة الشؤون الفنية - إلى وكالة الوزارة للأراضي والمساحة
- بشأن طلب إيقاف العمل على المواصفات القياسية (ساسو 2789)
- التأكيد على الجهات الحكومية بالعمل بالمادة الثامنة - من نظام الاستثمار التعديني
- بشأن تحديد مواقع محطات التحويل الرئيسية - للشركة السعودية للكهرباء
- بشأن إدراج المواقع الأثرية - ضمن اللائحة ذات الطبيعة الخاصة
- بشأن قرار مجلس الوزراء رقم (594) - الموافقة على تنظيم وزارة الاستثمار

### 📋 **قرارات وزارية** (8)
- إنشاء وحدة إدارية بمسمى إدارة تطوير المناطق العشوائية
- بشأن إعادة تشكيل لجنة بيع أراضي الوزارة
- إعادة تشكيل لجنة تقدير قيمة الأراضي البيضاء
- بشأن تجديد عضوية أعضاء لجنة النظر في مخالفات واعتراضات نظام رسوم الأراضي البيضاء
- إيقاف العمل بالمادة رقم (2.26) من القرار الوزاري رقم 4300000057-1
- قرار إطلاق المرحلة الأولى من برنامج رسوم الأراضي البيضاء لمدينة حائل
- الموافقة على اعتماد المعايير والضوابط التخطيطية المحدثة للمساجد
- إيقاف العمل بالتعميم الوزاري رقم 1326 بتاريخ 1429-1-7 - بشأن اقتراح السماح باستقطاع أجزاء من الحدائق العامة

### 🏛️ **قرارات مجلس الوزراء** (2)
- قرار المرصد الحضري
- صورة قرار مجلس الوزراء رقم (83) في 30-1-1443هـ - تشكيل اللجنة الوزارية الدائمة لفحص الاستثمارات الأجنبية

### 📊 **إحصائيات سريعة:**
- **المجموع:** 26 تشريع
- **تعاميم وزارية:** 11 (42%)
- **قرارات وزارية:** 8 (31%)
- **نظام كود البناء السعودي:** 5 (19%)
- **قرارات مجلس الوزراء:** 2 (8%)
- **الجهة المستهدفة:** جميع الموظفين (84%)، جهات كود البناء (16%)

**هذه هي جميع التشريعات المتاحة في النظام حالياً!** 📚"""

        return {
            "response": {
                "content": hardcoded_response,
                "metadata": {
                    "agent_type": self.agent_type,
                    "last_query": query,
                    "source": "hardcoded_list",
                    "total_results": 26
                }
            },
            "agent_type": self.agent_type,
            "status": "success"
        }

    async def _get_building_materials_response(self, query: str) -> Dict[str, Any]:
        """Hardcoded response for building materials queries."""
        logger.info("Handling building materials query")
        
        building_response = """## 🏗️ **التشريعات المتعلقة بمواد البناء والإنشاء**

### 📋 **نظام كود البناء السعودي** (5 تشريعات)

#### 🏛️ **النظام الأساسي:**
- **نظام تطبيق كود البناء السعودي** (م/43) - 1438/04/26
  - **الغرض:** إطار تشريعي شامل لتطبيق الكود
  - **الجهة:** وزارة الشؤون البلدية والقروية والإسكان

#### 📜 **اللوائح التنفيذية:**
- **اللائحة التنفيذية لنظام تطبيق كود البناء السعودي** (1213ق/أع39) - 1439/10/14
  - **الغرض:** تنظيم آليات التطبيق والتفتيش والإشغال
  
- **اللائحة التنفيذية لنظام تطبيق كود البناء السعودي - التعديل** (304) - 1444/07/08
  - **الغرض:** تحديث تطبيق كود البناء

#### 🔍 **لوائح التفتيش والمخالفات:**
- **لائحة متطلبات تعيين جهات التفتيش والمفتشين** (38299) - 1440/06/05
  - **الغرض:** تنظيم ترخيص جهات التفتيش والمفتشين
  - **الجهة:** اللجنة الوطنية لكود البناء السعودي

- **لائحة تصنيف مخالفات كود البناء السعودي** (1214ق/أع39) - 1439/10/14
  - **الغرض:** تنظيم العقوبات والغرامات وفق فئات الإشغال
  - **الجهة:** اللجنة الوطنية لكود البناء السعودي

### 📋 **تشريعات البناء الأخرى:**

#### 📢 **تعميم وزاري:**
- **محضر اتفاق تحديد نسب البناء ومجالات الاستثمار** - الأراضي والمباني الخاصة بوزارة البيئة والمياه والزراعة

#### 📋 **قرار وزاري:**
- **الموافقة على اعتماد المعايير والضوابط التخطيطية المحدثة للمساجد**

#### 📢 **تعميم وزاري (مواصفات):**
- **بشأن طلب إيقاف العمل على المواصفات القياسية (ساسو 2789)**

### 🏛️ **الجهات المختصة:**
- **وزارة الشؤون البلدية والقروية والإسكان** - النظام الأساسي واللوائح التنفيذية
- **اللجنة الوطنية لكود البناء السعودي** - التفتيش والمخالفات
- **وزارة البيئة والمياه والزراعة** - نسب البناء والاستثمار
- **الهيئة السعودية للمواصفات والمقاييس** - المواصفات القياسية

### 📊 **الملخص:**
- **المجموع:** 8 تشريعات مرتبطة بمواد البناء والإنشاء
- **نظام كود البناء السعودي:** 5 تشريعات (62%)
- **تشريعات البناء الأخرى:** 3 تشريعات (38%)
- **الجهة الرئيسية:** وزارة الشؤون البلدية والقروية والإسكان"""

        return {
            "response": {
                "content": building_response,
                "metadata": {
                    "agent_type": self.agent_type,
                    "last_query": query,
                    "source": "building_materials_specialist",
                    "total_results": 8
                }
            },
            "agent_type": self.agent_type,
            "status": "success"
        }

    async def _get_error_response(self, query: str, error: str) -> Dict[str, Any]:
        """Generate error response with helpful suggestions."""
        return {
            "response": {
                "content": f"""## ⚠️ **حدث خطأ غير متوقع**

🔍 **واجهت مشكلة أثناء معالجة سؤالك:** `{query}`

### 💡 **لا تقلق! يمكنني مساعدتك بطرق أخرى:**

🔢 **للإحصائيات:**
- كم عدد التشريعات؟
- توزيع التشريعات حسب النوع

📋 **لعرض التشريعات:**
- ما هي التشريعات المتاحة؟
- أظهر لي جميع التشريعات

🔍 **للبحث:**
- التشريعات عن الأراضي
- التشريعات الوزارية
- التشريعات عن البيئة

### 💬 **جرب سؤالاً آخر أو أعد صياغة سؤالك!**""",
                "metadata": {
                    "agent_type": self.agent_type,
                    "last_query": query,
                    "error": error
                }
            },
            "agent_type": self.agent_type,
            "status": "error"
        }

    def _format_response(self, response_content: str) -> str:
        """Format the AI response with proper structure."""
        if not response_content.strip():
            return "## 📄 **لم أتمكن من إنتاج إجابة مناسبة لهذا السؤال.**\n\n### 💡 **جرب سؤالاً آخر!**"
        
        # If response already has markdown formatting, return as is
        if response_content.startswith("#"):
            return response_content
        
        # Otherwise, add basic formatting
        return f"## 📄 **إجابة على سؤالك:**\n\n{response_content}"

    @property
    def agent_type(self) -> str:
        return "study" 