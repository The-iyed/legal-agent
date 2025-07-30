# Agent System

## Overview

The agent system is the core of Maarefa Agent V2, providing specialized handling for different types of queries through a modular and extensible architecture.

## Agent Types

### 1. Chat Agent
- **Purpose**: Handles general conversation and chat interactions
- **Prompt Types**: general, technical, creative
- **Use Cases**:
  - General conversation
  - Information requests
  - Casual interaction

### 2. Summarization Agent
- **Purpose**: Handles text summarization and content condensation
- **Prompt Types**: text, document, meeting
- **Use Cases**:
  - Text summarization
  - Document summarization
  - Meeting notes summarization

### 3. Study Agent
- **Purpose**: Provides overview of available studies
- **Prompt Types**: concept, problem, review, overview
- **Use Cases**:
  - Study material overview
  - Concept explanation
  - Study methodology guidance

### 4. Knowledge QA Agent
- **Purpose**: Handles specific content questions and knowledge retrieval
- **Prompt Types**: simple_qa, complex_qa
- **Use Cases**:
  - Factual questions
  - Complex queries
  - Knowledge retrieval

### 5. Clarification Agent
- **Purpose**: Helps clarify and refine user queries
- **Prompt Types**: general, technical, study
- **Use Cases**:
  - Query refinement
  - Concept clarification
  - Study-related clarification

## Agent Architecture

### Base Agent
```python
class BaseAgent:
    def __init__(self, settings: Settings):
        self.client = AzureOpenAI(...)
        self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME

    async def execute(self, query: str, prompt: str) -> Dict[str, Any]:
        # Main execution logic
        pass

    async def _process_query(self, query: str, prompt: str) -> str:
        # To be implemented by subclasses
        raise NotImplementedError()
```

### Agent Registry
```python
class AgentRegistry:
    _agent_classes: Dict[str, Dict[str, any]] = {
        "chat": {
            "class": ChatAgent,
            "name": "Chat Assistant",
            "description": "Handles general conversation"
        },
        # ... other agents
    }
```

## Agent Lifecycle

1. **Initialization**
   - Agent class registration
   - Settings configuration
   - Client initialization

2. **Query Processing**
   - Query analysis
   - Agent selection
   - Prompt selection
   - Response generation

3. **Response Handling**
   - Response formatting
   - Error handling
   - Result aggregation

## Adding New Agents

1. Create a new agent class:
```python
from .base_agent import BaseAgent

class NewAgent(BaseAgent):
    async def _process_query(self, query: str, prompt: str) -> str:
        # Implementation
        pass

    @property
    def agent_type(self) -> str:
        return "new_agent"
```

2. Register the agent:
```python
registry.register_agent(
    agent_type="new_agent",
    agent_class=NewAgent,
    prompt_types=["type1", "type2"]
)
```

## Best Practices

1. **Agent Implementation**
   - Inherit from BaseAgent
   - Implement _process_query
   - Define agent_type
   - Handle errors gracefully

2. **Prompt Management**
   - Use appropriate prompt types
   - Follow prompt guidelines
   - Maintain prompt consistency

3. **Error Handling**
   - Catch specific exceptions
   - Provide meaningful error messages
   - Log errors appropriately

4. **Performance**
   - Use async/await
   - Optimize API calls
   - Cache when appropriate

## Testing

1. **Unit Tests**
   - Test individual agent methods
   - Mock external dependencies
   - Verify error handling

2. **Integration Tests**
   - Test agent interactions
   - Verify prompt handling
   - Check response formats

3. **End-to-End Tests**
   - Test complete workflows
   - Verify system integration
   - Check performance 