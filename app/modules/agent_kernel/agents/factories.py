from typing import Optional
from ..core.interfaces import Agent, AgentFactory
from .chat_agent import ChatAgent
from .summarization_agent import SummarizationAgent
from .study_agent import StudyAgent
from .knowledge_qa_agent import KnowledgeQAAgent
from .clarification_agent import ClarificationAgent
from .context_aware_reformulator_agent import ContextAwareReformulatorAgent

class NormalChatFactory(AgentFactory):
    """Factory for creating normal chat agents."""
    
    def create_agent(self, agent_id: str) -> Optional[Agent]:
        """Create a normal chat agent instance."""
        return ChatAgent(agent_id)

class SummarizationFactory(AgentFactory):
    """Factory for creating summarization agents."""
    
    def create_agent(self, agent_id: str) -> Optional[Agent]:
        """Create a summarization agent instance."""
        return SummarizationAgent(agent_id)

class StudyFactory(AgentFactory):
    """Factory for creating study agents."""
    
    def create_agent(self, agent_id: str) -> Optional[Agent]:
        """Create a study agent instance."""
        return StudyAgent(agent_id)

class KnowledgeQAFactory(AgentFactory):
    """Factory for creating knowledge QA agents."""
    
    def create_agent(self, agent_id: str) -> Optional[Agent]:
        """Create a knowledge QA agent instance."""
        return KnowledgeQAAgent(agent_id)

class ClarificationFactory(AgentFactory):
    """Factory for creating clarification agents."""
    
    def create_agent(self, agent_id: str) -> Optional[Agent]:
        """Create a clarification agent instance."""
        return ClarificationAgent(agent_id)
class ContextAwareReformulatorFactory(AgentFactory):
    """Factory for creating context-aware reformulator agents."""
    
    def create_agent(self, agent_id: str) -> Optional[Agent]:
        """Create a context-aware reformulator agent instance."""
        return ContextAwareReformulatorAgent(agent_id)