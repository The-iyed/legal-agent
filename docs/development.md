# Development Guide

## Overview

This guide provides comprehensive instructions for developing and contributing to the Maarefa Agent V2 project. It covers setup, coding standards, testing, and deployment procedures.

## Development Environment Setup

### Prerequisites

1. **Python Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate  # Windows
   ```

2. **Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables**
   Create a `.env` file:
   ```env
   AZURE_OPENAI_API_KEY=your_api_key
   AZURE_OPENAI_ENDPOINT=your_endpoint
   AZURE_OPENAI_API_VERSION=2024-02-15-preview
   AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment
   ```

### Docker Setup

1. **Build Image**
   ```bash
   docker build -t maarefa-agent .
   ```

2. **Run Container**
   ```bash
   docker run -p 8000:8000 maarefa-agent
   ```

## Project Structure

```
maarefa-agent-v2/
├── app/
│   ├── api/
│   │   ├── endpoints/
│   │   └── models/
│   ├── core/
│   │   ├── config/
│   │   └── logging/
│   ├── modules/
│   │   ├── semantic_kernel/
│   │   └── prompt_manager/
│   └── main.py
├── tests/
├── docs/
└── docker/
```

## Coding Standards

### Python Style Guide

1. **PEP 8 Compliance**
   - Use 4 spaces for indentation
   - Maximum line length: 88 characters
   - Use meaningful variable names

2. **Type Hints**
   ```python
   from typing import Optional, Dict, Any

   def process_query(
       query: str,
       context: Optional[Dict[str, Any]] = None
   ) -> Dict[str, Any]:
       pass
   ```

3. **Docstrings**
   ```python
   def function_name(param1: str, param2: int) -> bool:
       """
       Brief description.

       Args:
           param1: Description of param1
           param2: Description of param2

       Returns:
           Description of return value

       Raises:
           ExceptionType: Description of when this exception occurs
       """
       pass
   ```

### Git Workflow

1. **Branch Naming**
   - Feature: `feature/feature-name`
   - Bugfix: `bugfix/bug-description`
   - Hotfix: `hotfix/issue-description`

2. **Commit Messages**
   ```
   type(scope): description

   [optional body]

   [optional footer]
   ```

3. **Pull Request Process**
   - Create feature branch
   - Write tests
   - Update documentation
   - Submit PR with description

## Testing

### Unit Tests

1. **Test Structure**
   ```python
   def test_function_name():
       # Arrange
       input_data = {...}
       expected = {...}

       # Act
       result = function(input_data)

       # Assert
       assert result == expected
   ```

2. **Running Tests**
   ```bash
   pytest tests/
   pytest tests/ -v  # verbose
   pytest tests/ -k "test_name"  # specific test
   ```

### Integration Tests

1. **Test Setup**
   ```python
   @pytest.fixture
   def test_client():
       app = create_app()
       with TestClient(app) as client:
           yield client
   ```

2. **API Tests**
   ```python
   def test_query_endpoint(test_client):
       response = test_client.post(
           "/query",
           json={"query": "test query"}
       )
       assert response.status_code == 200
   ```

## Adding New Features

### 1. New Agent

1. **Create Agent Class**
   ```python
   from app.modules.semantic_kernel.base_agent import BaseAgent

   class NewAgent(BaseAgent):
       def __init__(self, settings: Settings):
           super().__init__(settings)
           self.agent_type = "new_agent"
   ```

2. **Register Agent**
   ```python
   from app.modules.semantic_kernel.registry import AgentRegistry

   AgentRegistry.register_agent("new_agent", NewAgent)
   ```

### 2. New Prompt Type

1. **Create Prompt File**
   ```prompty
   # app/modules/prompt_manager/prompts/agent_type/new_prompt.prompty
   You are a new prompt type assistant...
   ```

2. **Update Registry**
   ```python
   AgentRegistry.register_prompt_type(
       "agent_type",
       "new_prompt"
   )
   ```

## Debugging

### Logging

1. **Configuration**
   ```python
   import logging

   logging.basicConfig(
       level=logging.DEBUG,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   ```

2. **Usage**
   ```python
   logger = logging.getLogger(__name__)
   logger.debug("Debug message")
   logger.info("Info message")
   logger.error("Error message")
   ```

### Error Handling

1. **Custom Exceptions**
   ```python
   class AgentError(Exception):
       """Base exception for agent errors."""
       pass

   class PromptError(AgentError):
       """Exception for prompt-related errors."""
       pass
   ```

2. **Error Handling**
   ```python
   try:
       result = process_query(query)
   except AgentError as e:
       logger.error(f"Agent error: {e}")
       raise HTTPException(status_code=500, detail=str(e))
   ```

## Performance Optimization

### 1. Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_function(param: str) -> str:
    return expensive_operation(param)
```

### 2. Async Operations

```python
async def async_process_query(query: str) -> Dict[str, Any]:
    result = await process_query_async(query)
    return result
```

## Deployment

### Docker Deployment

1. **Build**
   ```bash
   docker build -t maarefa-agent:latest .
   ```

2. **Run**
   ```bash
   docker run -d \
       -p 8000:8000 \
       --env-file .env \
       maarefa-agent:latest
   ```

### Production Considerations

1. **Environment Variables**
   - Use secure secret management
   - Never commit sensitive data
   - Use different configs for dev/prod

2. **Monitoring**
   - Set up logging
   - Configure metrics
   - Implement health checks

3. **Security**
   - Enable authentication
   - Use HTTPS
   - Implement rate limiting

## Contributing

### 1. Fork Repository

### 2. Create Branch
```bash
git checkout -b feature/new-feature
```

### 3. Make Changes
- Follow coding standards
- Write tests
- Update documentation

### 4. Submit PR
- Describe changes
- Link related issues
- Request review

## Troubleshooting

### Common Issues

1. **Docker Issues**
   ```bash
   # Clean up containers
   docker-compose down
   docker system prune

   # Rebuild
   docker-compose up --build
   ```

2. **Python Issues**
   ```bash
   # Update dependencies
   pip install -r requirements.txt --upgrade

   # Clear cache
   python -m pip cache purge
   ```

3. **API Issues**
   - Check logs
   - Verify environment variables
   - Test endpoints with curl

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Azure OpenAI Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Python Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [Docker Documentation](https://docs.docker.com/) 