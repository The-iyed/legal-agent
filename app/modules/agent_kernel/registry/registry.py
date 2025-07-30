from typing import Dict, Optional
from ..core.interfaces import Agent, AgentFactory
from ..core.types import AgentType
from ..agents.factories import NormalChatFactory, SummarizationFactory, StudyFactory, KnowledgeQAFactory, ClarificationFactory

class Registry:
    """Registry for managing agents and their factories."""
    
    def __init__(self):
        self._factories: Dict[AgentType, AgentFactory] = {}
        self._agents: Dict[str, Agent] = {}
        self._register_default_factories()
    
    def _register_default_factories(self):
        """Register default agent factories."""
        self.register_factory(AgentType.NORMAL_CHAT, NormalChatFactory())
        self.register_factory(AgentType.SUMMARIZATION, SummarizationFactory())
        self.register_factory(AgentType.STUDY, StudyFactory())
        self.register_factory(AgentType.KNOWLEDGE_QA, KnowledgeQAFactory())
        self.register_factory(AgentType.CLARIFICATION, ClarificationFactory())
    
    def register_factory(self, agent_type: AgentType, factory: AgentFactory):
        """Register a factory for an agent type."""
        self._factories[agent_type] = factory
    
    def create_agent(self, agent_type: AgentType) -> Optional[Agent]:
        """Create an agent instance for the given type."""
        # Check if we have a cached instance
        agent_id = f"{agent_type.value}-agent"
        if agent_id in self._agents:
            return self._agents[agent_id]
         
        factory = self._factories.get(agent_type)
        if factory:
            agent = factory.create_agent(agent_id)
            self._agents[agent_id] = agent
            return agent
        
        return None 