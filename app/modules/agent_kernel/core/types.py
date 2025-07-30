from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class AgentType(str, Enum):
    """Types of agents available in the system."""
    STUDIES_OVERVIEW = "studies-overview"
    KNOWLEDGE_STUDY = "knowledge-study"
    CLARIFICATION = "clarification"
    NORMAL_CHAT = "normal-chat"
    SUMMARIZATION = "summarization"
    CONTEXT_REFORMULATOR = "context_reformulator"

class Task(BaseModel):
    """Represents a task to be executed by an agent."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_type: AgentType
    input_data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TaskResult(BaseModel):
    """Represents the result of a task execution."""
    task_id: str
    agent_id: str
    status: str
    output: Dict[str, Any]
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    completed_at: datetime = Field(default_factory=datetime.utcnow) 