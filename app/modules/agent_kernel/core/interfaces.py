from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .types import Task, TaskResult

class Agent(ABC):
    """Interface for all agents in the system."""
    
    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """Execute a task and return the result."""
        pass

class AgentFactory(ABC):
    """Interface for creating agent instances."""
    
    @abstractmethod
    def create_agent(self, agent_id: str) -> Optional[Agent]:
        """Create an agent instance for the given ID."""
        pass 