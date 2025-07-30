from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
import logging

logger = logging.getLogger(__name__)


class ContextAwareReformulatorAgent(BaseAgent):
    """Agent for reformulating vague questions using conversation context."""
    
    def __init__(self, settings=None):
        super().__init__(settings)

    def _build_conversation_context(self, context: list) -> str:
        """
        Build a structured context string from all previous assistant responses in the conversation history.
        This allows the LLM to resolve references like 'the second point', 'the last legislation', etc.
        """
        if not context:
            return ""
        assistant_turns = []
        for msg in context:
            msg_data = msg.get("message_data", {})
            if msg_data.get("type") == "agent_response":
                content = msg_data.get("content", "")
                if content:
                    assistant_turns.append(content.strip())
        if not assistant_turns:
            return ""
        # Number the assistant turns for easier reference
        context_str = "\n\n".join([f"[Assistant Response {i+1}]:\n{resp}" for i, resp in enumerate(assistant_turns)])
        return context_str

    def _get_last_n_assistant_responses(self, context: list, n: int = 3) -> list:
        """
        Get the last n assistant (agent) responses from the conversation history.
        Returns a list of strings, most recent first.
        """
        if not context:
            return []
        assistant_turns = []
        for msg in reversed(context):
            msg_data = msg.get("message_data", {})
            if msg_data.get("type") == "agent_response":
                content = msg_data.get("content", "")
                if content:
                    assistant_turns.append(content.strip())
                if len(assistant_turns) == n:
                    break
        return assistant_turns

    async def _process_query(self, messages: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Process a query to reformulate vague questions using context.
        
        Args:
            messages: Pre-prepared messages for the API
            
        Returns:
            The reformulated query or original if no reformulation needed
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=0.3
            )
            
            response = completion.choices[0].message.content
            logger.info(f"Context reformulator response: {response[:100]}...")
            return response
            
        except Exception as e:
            logger.error(f"Error in context reformulation: {str(e)}")
            return "فشل في إعادة صياغة السؤال. يرجى إعادة طرح السؤال بوضوح أكبر."
        
    async def execute(
        self, query: str, prompt: str, context: Optional[list] = None
    ) -> dict:
        """
        Execute the context reformulation process.
        
        Args:
            query: The user's potentially vague query
            prompt: The system prompt for reformulation
            context: Conversation history
            
        Returns:
            Response containing reformulated query or original query
        """
        try:
            logger.info("Context reformulator agent executing - supervisor has routed query for reformulation")
            # Get the last three assistant responses (most recent first)
            last_responses = self._get_last_n_assistant_responses(context, 3) if context else []
            if not last_responses:
                logger.warning("No assistant responses available in context for reformulation")
                return {
                    "response": {
                        "content": query,
                        "metadata": {
                            "reformulated": False,
                            "reason": "No assistant responses in context for reformulation"
                        }
                    },
                    "agent_type": self.agent_type,
                    "status": "success"
                }
            # Build the system prompt with the last three responses
            system_prompt = f"""
            {prompt}

            المهمة: إذا كان السؤال يشير إلى نقطة أو عنصر مرقم في الرسائل السابقة (مثل: النقطة الثالثة)، استخرج نص النقطة أو العنصر المشار إليه من الرسائل الثلاث الأخيرة للمساعد (المذكورة أدناه بترقيم واضح)، ثم أعد صياغة السؤال ليكون مباشراً حول هذا النص، وليس حول ترتيبه أو رقمه.

            مثال:
            السؤال الأصلي: "ما هي النقطة الثالثة في قائمة التشريعات؟"
            النقطة الثالثة في الرسالة: "إعادة تشكيل لجنة تقدير قيمة الأراضي البيضاء"
            السؤال المُعاد صياغته: "ما تفاصيل قرار إعادة تشكيل لجنة تقدير قيمة الأراضي البيضاء؟"

            إذا لم تجد النقطة أو العنصر المطلوب، اطلب من المستخدم التوضيح.

            السؤال الأصلي: {query}

            آخر ثلاث رسائل من المساعد (الأحدث أولاً):
            [1]: {last_responses[0] if len(last_responses) > 0 else ''}
            [2]: {last_responses[1] if len(last_responses) > 1 else ''}
            [3]: {last_responses[2] if len(last_responses) > 2 else ''}

            التعليمات:
            - إذا وجدت ما يشير إليه المستخدم في إحدى هذه الرسائل، أعد صياغة السؤال ليكون مباشراً حول النص الفعلي.
            - إذا لم تجد أي محتوى مناسب، أخبر المستخدم أن يوضح النقطة أو العنصر الذي يقصده.
            """
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"أعد صياغة هذا السؤال: {query}"}
            ]
            reformulated_query = await self._process_query(messages)
            logger.info(f"Query reformulated from: '{query}' to: '{reformulated_query[:100]}...'")
            return {
                "response": {
                    "content": reformulated_query,
                    "metadata": {
                        "reformulated": reformulated_query != query,
                        "original_query": query,
                        "context_used": last_responses
                    }
                },
                "agent_type": self.agent_type,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error in context reformulator execution: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "agent_type": self.agent_type,
                "status": "error"
            }

    @property
    def agent_type(self) -> str:
        """Get the type of this agent."""
        return "context_reformulator"