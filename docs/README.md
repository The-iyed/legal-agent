# Maarefa Agent V2

A sophisticated AI agent system built with FastAPI and Azure OpenAI, designed to handle various types of queries through specialized agents.

## Features

- Multiple specialized agents for different types of queries:
  - Chat Agent: General conversation and interactions
  - Summarization Agent: Text and content summarization
  - Study Agent: Study materials and methodology
  - Knowledge QA Agent: Specific content questions
  - Clarification Agent: Query refinement and clarification

- Dynamic prompt management system
- Azure OpenAI integration
- Docker-based deployment
- FastAPI backend

## Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Azure OpenAI API access

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name

# Application Configuration
APP_ENV=development
PORT=8000
```

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/yourusername/maarefa-agent-v2.git
cd maarefa-agent-v2
```

2. Create and configure your `.env` file

3. Build and run with Docker:
```bash
docker-compose up --build
```

4. Access the API at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## New Architecture Diagram

![New Architecture Diagram](docs/new_architecture.png)

## Project Structure

```
maarefa-agent-v2/
├── app/
│   ├── api/
│   │   └── endpoints/
│   ├── core/
│   │   └── config/
│   ├── modules/
│   │   ├── agent_kernel/
│   │   ├── prompt_manager/
│   │   └── semantic_kernel/
│   └── main.py
├── docs/
├── tests/
├── .env
├── docker-compose.yml
└── Dockerfile
```

## Documentation

- [Architecture Overview](architecture.md)
- [Agent System](agents.md)
- [Prompt Management](prompts.md)
- [API Reference](api.md)
- [Development Guide](development.md)

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 