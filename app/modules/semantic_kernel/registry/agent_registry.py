import logging
from typing import Dict, List, Type, Optional, Any
from ...agent_kernel.agents.base_agent import BaseAgent
from ...agent_kernel.agents.chat_agent import ChatAgent
from ...agent_kernel.agents.summarization_agent import SummarizationAgent
from ...agent_kernel.agents.study_agent import StudyAgent
from ...agent_kernel.agents.knowledge_qa_agent import KnowledgeQAAgent
from ...agent_kernel.agents.more_content_agent import MoreContentAgent
from ...agent_kernel.agents.clarification_agent import ClarificationAgent
from ...agent_kernel.agents.context_aware_reformulator_agent import ContextAwareReformulatorAgent
from langgraph.graph import StateGraph, END
from ....core.config.settings import get_settings
from ...agent_kernel.core.types import AgentType 

logger = logging.getLogger(__name__)

class AgentRegistry:
    """Registry for managing different types of agents, their prompts, and workflows."""
    

    _agent_classes: Dict[str, Dict[str, any]] = {
        "chat": {
            "class": ChatAgent,
            "name": "Chat Assistant",
            "description": "Handles general conversation and chat interactions"
        },
        "summarization": {
            "class": SummarizationAgent,
            "name": "Summarization Assistant",
            "description": "Handles text summarization"
        },
        "study": {
            "class": StudyAgent,
            "name": "Legislation Overview Agent",
            "description": """Provides comprehensive overview and analysis of available legislation subjects.
            Handles queries about legislation topics using Excel data analysis ( like ما هي التشريعات المتاحة؟, كم عدد التشريعات حول البيئة؟)
            Specializes in browsing, counting, filtering, and categorizing legislation by subject, type, issuing authority, and year."""
        },
        "knowledge_qa": {
            "class": KnowledgeQAAgent,
            "name": "Legislative Expert",
            "description": """Handles specific legislative questions, legal document retrieval,
            summarization about legislative topics in the legislative library ( like لخص موضوع قانون حماية البيئة)
            generating reports or summaries based on legislative documents and legal content."""
        },
        "more_content": {
            "class": MoreContentAgent,
            "name": "More Content Provider",
            "description": "Handles requests for more information on a previously discussed topic by fetching subsequent results"
        },
        "context_reformulator": {
            "class": ContextAwareReformulatorAgent,
            "name": "Context Reformulator",
            "description": """Detects and reformulates queries that reference previous context or specific elements from prior responses. 
            Handles any pointing references such as: "النقطة الأخيرة/الثانية/التاسعة", "التشريع الثالث", "القرار المذكور", 
            "النقطة الثانية", "الموضوع السابق", "explain the second point", "the ninth legislation", "that point", etc.
            Extracts the exact referenced content from conversation history and reformulates questions to be explicit and self-contained 
            for better processing by specialist agents."""
        },
        "legal_basis": {
            "class": __import__("app.modules.agent_kernel.agents.legal_basis_agent", fromlist=["LegalBasisAgent"]).LegalBasisAgent,
            "name": "Legal Basis Analyzer",
            "description": "Analyzes claim and attachments, fetches laws, synthesizes legal basis and defense points"
        },
        "phase_advisor": {
            "class": __import__("app.modules.agent_kernel.agents.phase_advisor_agent", fromlist=["PhaseAdvisorAgent"]).PhaseAdvisorAgent,
            "name": "Phase Advisor",
            "description": "Advises on next steps after legal-basis phase (attachments or proceed to drafting)"
        },
    }
    

    _agent_prompt_types: Dict[str, List[str]] = {
        "chat": ["default"],
        "summarization": ["for_history"],
        "study": ["general_query"],
        "knowledge_qa": ["simple_qa", "comparison"],
        "more_content": ["simple_qa"],
        "context_reformulator": ["default"],
        "legal_basis": ["extract_issues", "search_plan", "analysis", "defense", "update", "pleading"],
        "phase_advisor": ["legal_basis_next_steps"],
    }


    _workflows: Dict[str, Type[StateGraph]] = {}

    @classmethod
    def register_workflow(cls, workflow_name: str, workflow_graph: Type[StateGraph]) -> None:
        """
        Register a new workflow graph.
        
        Args:
            workflow_name: The name of the workflow
            workflow_graph: The compiled LangGraph StateGraph
        """
        if workflow_name in cls._workflows:
            raise ValueError(f"Workflow '{workflow_name}' already registered")
        logger.info(f"Registered workflow: {workflow_name}")
        cls._workflows[workflow_name] = workflow_graph

    @classmethod
    def get_workflow(cls, workflow_name: str) -> Optional[Type[StateGraph]]:
        """
        Get a registered workflow graph.
        
        Args:
            workflow_name: The name of the workflow to retrieve
            
        Returns:
            The workflow graph if found, None otherwise
        """
        logger.info(f"Retrieving workflow: {workflow_name}")
        return cls._workflows.get(workflow_name)

    @classmethod
    async def _run_agent_step_in_workflow(cls, agent_type: str, query: str, prompt_type: str, settings: Any) -> Dict[str, Any]:
        """Helper to run a single agent step within a workflow from the registry."""
        logger.info(f"Executing agent step: {agent_type} with prompt_type: {prompt_type}")
        agent_class = cls.get_agent_class(agent_type)
        if not agent_class:
            raise ValueError(f"Agent class for {agent_type} not found.")
        agent = agent_class(settings=settings) # Pass settings to agent constructor
        result = await agent.execute(query, prompt_type)
        logger.info(f"Agent step {agent_type} completed. Result status: {result.get('status')}")
        return result

    @classmethod
    async def _run_study_agent_node(cls, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node for running the Study Agent in a LangGraph workflow."""
        query = state["query"]
        settings = state["settings"] # Get settings from state
        prompt_type = "overview"  # Default prompt for study agent in this workflow
        logger.info(f"Starting Study Agent node for query: {query[:50]}...")
        result = await cls._run_agent_step_in_workflow(AgentType.STUDIES_OVERVIEW.value, query, prompt_type, settings)
        state["study_output"] = result.get("response", {}).get("content")
        state["study_error"] = result.get("error")
        logger.info(f"Study Agent node completed. Study output length: {len(state.get('study_output', ''))}")
        return state

    @classmethod
    async def _run_summarization_agent_node(cls, state: Dict[str, Any]) -> Dict[str, Any]:
        """Node for running the Summarization Agent in a LangGraph workflow."""
        study_output = state.get("study_output", "")
        settings = state["settings"] # Get settings from state
        if not study_output:
            state["error"] = "No study output to summarize."
            logger.warning("Summarization node: No study output found, skipping summarization.")
            return state

        query = f"Summarize the following text: {study_output}"
        prompt_type = "text"  # Default prompt for summarization agent in this workflow
        logger.info(f"Starting Summarization Agent node for study output (length {len(study_output)}).")
        result = await cls._run_agent_step_in_workflow(AgentType.SUMMARIZATION.value, query, prompt_type, settings)
        state["summarization_output"] = result.get("response", {}).get("content")
        state["summarization_error"] = result.get("error")
        logger.info(f"Summarization Agent node completed. Summarization output length: {len(state.get('summarization_output', ''))}")
        return state

    @classmethod
    def _build_study_summarization_workflow(cls) -> Type[StateGraph]:
        """
        Builds and returns the study summarization workflow graph.
        This workflow takes the output from the study agent and passes it to the summarization agent.
        """
        logger.info("Building study_summarization workflow graph.")
        workflow = StateGraph(Dict[str, Any])

        workflow.add_node("study_agent_node", cls._run_study_agent_node)
        workflow.add_node("summarization_agent_node", cls._run_summarization_agent_node)

        workflow.set_entry_point("study_agent_node")
        workflow.add_edge("study_agent_node", "summarization_agent_node")
        workflow.add_edge("summarization_agent_node", END)

        return workflow.compile()

    def __init__(self):
        if not AgentRegistry._workflows:
            AgentRegistry.register_workflow("study_summarization", AgentRegistry._build_study_summarization_workflow())

    @classmethod
    def get_agent_class(cls, agent_type: str) -> Optional[Type[BaseAgent]]:
        """
        Get the agent class for a given type.
        
        Args:
            agent_type: The type of agent to get
            
        Returns:
            The agent class if found, None otherwise
        """
        agent_info = cls._agent_classes.get(agent_type)
        return agent_info["class"] if agent_info else None
    
    @classmethod
    def get_agent_name(cls, agent_type: str) -> Optional[str]:
        """
        Get the display name for a given agent type.
        
        Args:
            agent_type: The type of agent to get the name for
            
        Returns:
            The agent name if found, None otherwise
        """
        agent_info = cls._agent_classes.get(agent_type)
        return agent_info["name"] if agent_info else None
    
    @classmethod
    def get_agent_description(cls, agent_type: str) -> Optional[str]:
        agent_info = cls._agent_classes.get(agent_type)
        return agent_info["description"] if agent_info else None
    
    @classmethod
    def get_required_prompt_types(cls, agent_type: str) -> List[str]:
        return cls._agent_prompt_types.get(agent_type, [])
    
    @classmethod
    def get_available_agent_types(cls) -> List[Dict[str, str]]:
        return [
            {
                "type": agent_type,
                "name": info["name"],
                "description": info["description"],
            }
            for agent_type, info in cls._agent_classes.items()
        ]
    
    @classmethod
    def register_agent(cls, agent_type: str, agent_class: Type, prompt_types: List[str]) -> None:
        if agent_type in cls._agent_classes:
            raise ValueError(f"Agent type '{agent_type}' already registered")
        
        cls._agent_classes[agent_type] = {
            "class": agent_class,
            "name": "",
            "description": ""
        }
        cls._agent_prompt_types[agent_type] = prompt_types
    
    @classmethod
    def unregister_agent(cls, agent_type: str) -> None:
        """
        Unregister an agent type."""
        if agent_type not in cls._agent_classes:
            raise ValueError(f"Agent type '{agent_type}' not registered")
        
        del cls._agent_classes[agent_type]
        del cls._agent_prompt_types[agent_type] 
