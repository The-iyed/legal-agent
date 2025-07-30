# API Reference

## Overview

The Maarefa Agent V2 API provides endpoints for interacting with the agent system. The API is built with FastAPI and provides both REST endpoints and automatic OpenAPI documentation.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication. Future versions may implement authentication mechanisms.

## Endpoints

### Query Processing

#### POST /query

Process a query using the agent system.

**Request Body:**
```json
{
    "query": "string",
    "context": {
        "user_id": "string",
        "additional_context": "any"
    }
}
```

**Response:**
```json
{
    "agent_type": "string",
    "prompt_type": "string",
    "confidence": "float",
    "response": {
        "content": "string",
        "metadata": {}
    },
    "error": "string",
    "reasoning": "string"
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{
         "query": "What are the available studies?",
         "context": {
             "user_id": "123"
         }
     }'
```

**Example Response:**
```json
{
    "agent_type": "study",
    "prompt_type": "overview",
    "confidence": 0.85,
    "response": {
        "content": "Here are the available studies...",
        "metadata": {
            "study_count": 5
        }
    },
    "error": null,
    "reasoning": "Query is asking for study overview"
}
```

## Error Handling

### Error Response Format
```json
{
    "detail": "string"
}
```

### Common Error Codes

- `400 Bad Request`: Invalid request format
- `404 Not Found`: Endpoint not found
- `500 Internal Server Error`: Server-side error

## Response Types

### QueryResponse
```python
class QueryResponse(BaseModel):
    agent_type: str
    prompt_type: str
    confidence: float
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    reasoning: Optional[str] = None
```

### QueryRequest
```python
class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None
```

## Agent Types

The API supports the following agent types:

1. **chat**
   - General conversation
   - Technical discussion
   - Creative interaction

2. **summarization**
   - Text summarization
   - Document summarization
   - Meeting summarization

3. **study**
   - Concept explanation
   - Problem solving
   - Material review
   - Study overview

4. **knowledge_qa**
   - Simple questions
   - Complex queries
   - Knowledge retrieval

5. **clarification**
   - General clarification
   - Technical clarification
   - Study clarification

## Best Practices

1. **Request Formatting**
   - Use proper JSON formatting
   - Include necessary context
   - Keep queries clear and specific

2. **Error Handling**
   - Check response status codes
   - Handle error responses
   - Implement retry logic

3. **Performance**
   - Keep requests concise
   - Minimize context data
   - Cache when appropriate

## Rate Limiting

Currently, there are no rate limits implemented. Future versions may include rate limiting based on:
- Requests per minute
- Requests per hour
- User-based limits

## Versioning

The API version is included in the URL path:
```
http://localhost:8000/v1/query
```

## Documentation

The API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Examples

### Basic Query
```python
import requests

response = requests.post(
    "http://localhost:8000/query",
    json={
        "query": "What are the available studies?",
        "context": {"user_id": "123"}
    }
)
print(response.json())
```

### Error Handling
```python
import requests
from requests.exceptions import RequestException

try:
    response = requests.post(
        "http://localhost:8000/query",
        json={"query": "Invalid query"}
    )
    response.raise_for_status()
except RequestException as e:
    print(f"Error: {e}")
```

### Context Usage
```python
import requests

context = {
    "user_id": "123",
    "previous_queries": ["query1", "query2"],
    "user_preferences": {
        "language": "en",
        "detail_level": "high"
    }
}

response = requests.post(
    "http://localhost:8000/query",
    json={
        "query": "Explain the study concept",
        "context": context
    }
)
print(response.json())
``` 