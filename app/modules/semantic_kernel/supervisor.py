from typing import Dict, Any, Optional, List
import json
from .registry.agent_registry import AgentRegistry
from ...core.config.settings import get_settings
from openai import AzureOpenAI
from langgraph.graph import StateGraph, END
from ..agent_kernel.core.types import AgentType # Import AgentType
from ..prompt_manager.manager import PromptManager
import logging

logger = logging.getLogger(__name__)

class Supervisor:
    """Supervisor class for managing agent interactions and query routing."""
    
    def __init__(self):
        """Initialize the supervisor with settings and registry."""
        self.settings = get_settings()
        self.registry = AgentRegistry()
        self.prompt_manager = PromptManager()
        
        # Initialize Azure OpenAI client with settings
        if not all([
            self.settings.AZURE_OPENAI_API_KEY,
            self.settings.AZURE_OPENAI_ENDPOINT,
            self.settings.AZURE_OPENAI_DEPLOYMENT_NAME
        ]):
            raise ValueError("Missing required Azure OpenAI settings")
            
        self.client = AzureOpenAI(
            api_key=self.settings.AZURE_OPENAI_API_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT
        )
        self.deployment_name = self.settings.AZURE_OPENAI_DEPLOYMENT_NAME
    
    async def analyze_query(self, query: str, context: Optional[List[Dict[str, Any]]] = None, available_agents: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Analyze the query to determine which agent should handle it.
        Optionally restrict to a provided list of available_agents.
        """
        logger.info(f"Analyzing query: {query[:100]}...")
        # Use provided available_agents or all from registry
        agents_to_consider = available_agents or self.registry.get_available_agent_types()
        agent_descriptions = "\n".join([
            f"- {agent['type']}: {agent['description']} (Prompt Types: {', '.join(self.registry.get_required_prompt_types(agent['type']))})"
            for agent in agents_to_consider
        ])
        system_prompt = f"""You are a query analyzer. Your task is to determine which type of agent should handle the query and what prompt type is most suitable for that agent based on the query.\n        Available agents and their prompt types:\n        {agent_descriptions}\n        \n        Return a JSON with:\n        - agent_type: one of the available agent types\n        - prompt_type: the most suitable prompt type for the selected agent_type, from the list of available prompt types for that agent.\n        - confidence: a number between 0 and 1\n        - reasoning: brief explanation of your decision"""
        analysis_messages = [{"role": "system", "content": system_prompt}]
        if context:
            logger.info(f"Analyzer: Adding {len(context)} messages from conversation history to analysis.")
            for msg in context:
                msg_type = msg.get("message_data", {}).get("type", "")
                content = msg.get("message_data", {}).get("content", "")
                if msg_type == "user_message":
                    analysis_messages.append({"role": "user", "content": content})
                elif msg_type == "agent_response":
                    analysis_messages.append({"role": "assistant", "content": content})
        analysis_messages.append({"role": "user", "content": query})
        logger.info(f"Analyzer: Total messages for analysis: {len(analysis_messages)}")
        try:
            completion = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=analysis_messages,
                response_format={"type": "json_object"}
            )
            analysis = json.loads(completion.choices[0].message.content)
            logger.info(f"Query analysis complete: Agent Type='{analysis.get('agent_type')}', Prompt Type='{analysis.get('prompt_type')}', Confidence={analysis.get('confidence')}")
            if not isinstance(analysis, dict):
                raise ValueError("Analysis result is not a dictionary")
            required_fields = ["agent_type", "prompt_type", "confidence", "reasoning"]
            for field in required_fields:
                if field not in analysis:
                    raise ValueError(f"Missing required field: {field}")
            selected_agent_type = analysis['agent_type']
            selected_prompt_type = analysis['prompt_type']
            valid_prompt_types = self.registry.get_required_prompt_types(selected_agent_type)
            if selected_prompt_type not in valid_prompt_types:
                logger.warning(f"Invalid prompt_type '{selected_prompt_type}' for agent_type '{selected_agent_type}'. Falling back to default.")
                analysis['prompt_type'] = valid_prompt_types[0] if valid_prompt_types else "default" 
            return analysis
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis result: {str(e)}")
            raise ValueError(f"Failed to parse analysis result: {str(e)}")
        except Exception as e:
            logger.error(f"Error during query analysis: {str(e)}")
            raise ValueError(f"Error during query analysis: {str(e)}")
    
    async def route_query(self, query: str, context: Optional[List[Dict[str, Any]]] = None, system_prompt: Optional[str] = None, conversation_status: Optional[str] = None) -> Dict[str, Any]:
        try:
            logger.info(f"Routing query: {query[:100]}...")
            
            # Check if conversation status is "waiting_for_claim" - automatically route to chat agent
            if conversation_status == "waiting_for_claim":
                logger.info("Conversation status is 'waiting_for_claim' - automatically routing to chat agent without LLM analysis")
                agent_type = "chat"
                confidence = 1.0
                reasoning = "Automatic routing due to waiting_for_claim status"
                prompt_type = "waiting_for_claim"
            elif conversation_status == "waiting_for_attachments":
                logger.info("Conversation status is 'waiting_for_attachments' - automatically routing to chat agent without LLM analysis")
                agent_type = "chat"
                confidence = 1.0
                reasoning = "Automatic routing due to waiting_for_attachments status"
                prompt_type = "waiting_for_attachments"
            elif conversation_status == "claim_discussion":
                logger.info("Conversation status is 'claim_discussion' - routing to chat agent with claim discussion prompt")
                agent_type = "chat"
                confidence = 1.0
                reasoning = "Automatic routing due to claim_discussion status"
                prompt_type = "claim_discussion"
            elif conversation_status == "claim_docs_discussion":
                logger.info("Conversation status is 'claim_docs_discussion' - routing to chat agent with claim_docs_discussion prompt")
                agent_type = "chat"
                confidence = 1.0
                reasoning = "Automatic routing due to claim_docs_discussion status"
                prompt_type = "claim_docs_discussion"
            else:
                # First analysis with all agents
                analysis = await self.analyze_query(query, context)
                agent_type = analysis["agent_type"]
                confidence = float(analysis["confidence"])
                reasoning = analysis["reasoning"]
                prompt_type = analysis["prompt_type"]

            # If the chosen agent is the context reformulator, run it ONCE
            if agent_type == "context_reformulator":
                logger.info("Context reformulator selected, running reformulation...")
                # Get reformulator agent and prompt
                reformulator_class = self.registry.get_agent_class("context_reformulator")
                reformulator_prompt = self.prompt_manager.get_prompt("context_reformulator", "default")
                if not reformulator_class or not reformulator_prompt:
                    logger.warning("Context reformulator agent or prompt not found, falling back to original query.")
                else:
                    reformulator = reformulator_class(settings=self.settings)
                    result = await reformulator.execute(query, reformulator_prompt, context=context)
                    response = result.get("response", {})
                    reformulated_query = response.get("content", query)
                    logger.info(f"Reformulated query: {reformulated_query}")
                    # Now re-analyze, but exclude the reformulator
                    available_agents = [agent for agent in self.registry.get_available_agent_types() if agent["type"] != "context_reformulator"]
                    analysis = await self.analyze_query(reformulated_query, context, available_agents=available_agents)
                    agent_type = analysis["agent_type"]
                    confidence = float(analysis["confidence"])
                    reasoning = analysis["reasoning"]
                    prompt_type = analysis["prompt_type"]
                    query = reformulated_query  # Use the reformulated query for the final agent

            if agent_type == AgentType.STUDIES_OVERVIEW.value and "summarize" in query.lower():
                logger.info(f"Triggering 'study_summarization' workflow for agent_type: {agent_type}")
                workflow_app = self.registry.get_workflow("study_summarization")
                if not workflow_app:
                    logger.error("Study summarization workflow not registered.")
                    raise ValueError("Study summarization workflow not registered.")

                initial_state = {"query": query, "settings": self.settings}
                final_state = await workflow_app.ainvoke(initial_state)

                if final_state.get("summarization_error") or final_state.get("error"):
                    logger.error(f"Workflow execution failed. Error: {final_state.get('summarization_error') or final_state.get('error')}")
                    return {
                        "agent_type": AgentType.SUMMARIZATION.value,
                        "prompt_type": prompt_type,
                        "confidence": 0.0,
                        "response": None,
                        "error": final_state.get("summarization_error") or final_state.get("error"),
                        "reasoning": "Workflow execution failed"
                    }
                else:
                    logger.info(f"Workflow 'study_summarization' completed successfully. Summarized output length: {len(final_state.get('summarization_output', ''))}")
                    return {
                        "agent_type": AgentType.SUMMARIZATION.value,
                        "prompt_type": prompt_type,
                        "confidence": 1.0, # High confidence for successful workflow
                        "response": {"content": final_state.get("summarization_output"), "metadata": {}},
                        "error": None,
                        "reasoning": "Successfully executed study summarization workflow"
                    }
            

            agent_class = self.registry.get_agent_class(agent_type)
            
            if not agent_class:
                logger.error(f"Agent type '{agent_type}' not found for single agent routing.")
                return {
                    "agent_type": agent_type,
                    "prompt_type": "general",
                    "confidence": 0.0,
                    "response": None,
                    "error": f"Agent type '{agent_type}' not found",
                    "reasoning": "Failed to find appropriate agent"
                }
            
            # Get the actual prompt text from the PromptManager or use provided system_prompt
            if system_prompt:
                prompt = system_prompt
                logger.info("Using provided system prompt for agent execution")
            else:
                prompt = self.prompt_manager.get_prompt(agent_type, prompt_type)
                if not prompt:
                    logger.error(f"Prompt not found for agent_type '{agent_type}' and prompt_type '{prompt_type}'")
                    return {
                        "agent_type": agent_type,
                        "prompt_type": prompt_type,
                        "confidence": 0.0,
                        "response": None,
                        "error": f"Prompt not found for agent_type '{agent_type}' and prompt_type '{prompt_type}'",
                        "reasoning": "Failed to find appropriate prompt"
                    }

            # Inject claim raw text into claim_discussion prompt if available
            if prompt_type == "claim_discussion":
                try:
                    from app.core.database import get_database
                    db = get_database()
                    conv_id = None
                    # Try to extract conversation_id from context messages metadata
                    if context:
                        for msg in context:
                            cid = msg.get("conversation_id") or msg.get("message_data", {}).get("conversation_id")
                            if cid:
                                conv_id = cid
                                break
                    # Fallback: try last message ref
                    if not conv_id and context and len(context) > 0:
                        conv_id = context[-1].get("conversation_id")
                    if conv_id:
                        doc = await db.statement_of_claim.find_one({"conversation_id": conv_id})
                        raw_text = (doc or {}).get("raw_text")
                        if raw_text:
                            prompt = prompt.replace("{{RAW_CLAIM_TEXT}}", raw_text)
                        else:
                            prompt = prompt.replace("{{RAW_CLAIM_TEXT}}", "(لا يوجد نص مستخرج محفوظ لهذه القضية حتى الآن)")
                    else:
                        prompt = prompt.replace("{{RAW_CLAIM_TEXT}}", "(يتعذر تحديد المحادثة لاستخراج النص)")
                except Exception as e:
                    logger.warning(f"Could not inject RAW_CLAIM_TEXT into claim_discussion prompt: {e}")
                    prompt = prompt.replace("{{RAW_CLAIM_TEXT}}", "(تعذر تحميل نص الدعوى المحفوظ)")
            
            # For claim_docs_discussion, inject attachments raw text
            if prompt_type == "claim_docs_discussion":
                try:
                    from app.core.database import get_database
                    db = get_database()
                    conv_id = None
                    if context:
                        for msg in context:
                            cid = msg.get("conversation_id") or msg.get("message_data", {}).get("conversation_id")
                            if cid:
                                conv_id = cid
                                break
                    if conv_id:
                        # gather attachments texts
                        texts = []
                        cursor = db.attachments.find({"conversation_id": conv_id}).sort("created_at", 1)
                        async for att in cursor:
                            t = (att.get("extracted_content", {}) or {}).get("raw_text", "")
                            if t:
                                texts.append(t[:2000])
                        merged = "\n\n---\n".join(texts) if texts else "(لا توجد مرفقات محفوظة)"
                        prompt = prompt.replace("{{RAW_ATTACHMENTS_TEXT}}", merged)
                    else:
                        prompt = prompt.replace("{{RAW_ATTACHMENTS_TEXT}}", "(يتعذر تحديد المحادثة لاستخراج نصوص المرفقات)")
                except Exception as e:
                    logger.warning(f"Could not inject RAW_ATTACHMENTS_TEXT: {e}")
                    prompt = prompt.replace("{{RAW_ATTACHMENTS_TEXT}}", "(تعذر تحميل نصوص المرفقات)")

            # Process the query with the selected agent
            agent = agent_class(settings=self.settings)
            logger.info(f"Supervisor: Passing context to agent.execute. Context length: {len(context) if context else 0}")
            agent_response = await agent.execute(query, prompt, context=context)
            
            # Extract the actual response content from the agent response
            if agent_response.get("error"):
                # Handle agent errors
                return {
                    "agent_type": agent_type,
                    "prompt_type": prompt_type,
                    "confidence": 0.0,
                    "response": None,
                    "error": agent_response["error"],
                    "reasoning": f"Agent execution failed: {agent_response['error']}"
                }
            
            # Extract response content - handle different agent response formats
            response_content = agent_response.get("response", {})
            if isinstance(response_content, dict) and "content" in response_content:
                # KnowledgeQA agent format: {"response": {"content": "...", "metadata": {...}}}
                extracted_response = response_content
            elif isinstance(response_content, str):
                # Simple string response format
                extracted_response = {"content": response_content, "metadata": {}}
            else:
                # Fallback - convert to string
                extracted_response = {"content": str(response_content), "metadata": {}}
            
            logger.info(f"Supervisor: Extracted response format - content length: {len(extracted_response.get('content', ''))}")
            
            return {
                "agent_type": agent_type,
                "prompt_type": prompt_type,
                "confidence": confidence,
                "response": extracted_response,
                "error": None,
                "reasoning": reasoning
            }
            
        except Exception as e:
            logger.error(f"Error during query routing: {str(e)}", exc_info=True)
            return {
                "agent_type": "chat", # Default to chat agent for errors
                "prompt_type": "general",
                "confidence": 0.0,
                "response": {"content": f"An error occurred: {str(e)}"},
                "error": str(e),
                "reasoning": "Error processing query"
            }