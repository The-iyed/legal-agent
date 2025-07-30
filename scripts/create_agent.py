#!/usr/bin/env python3

import os
import sys
import argparse
from pathlib import Path
from typing import List

def create_agent_class(agent_name: str, prompt_types: List[str]) -> str:
    """Generate the agent class code."""
    class_name = ''.join(word.capitalize() for word in agent_name.split('_'))
    agent_type = agent_name.lower()
    
    return f'''from typing import Dict, Any
from ...agent_kernel.agents.base_agent import BaseAgent
from ....core.config.settings import Settings

class {class_name}(BaseAgent):
    """{class_name} for handling {agent_type} related queries."""
    
    def __init__(self, settings: Settings):
        """Initialize the {class_name}.
        
        Args:
            settings: Application settings
        """
        super().__init__(settings)
        self.agent_type = "{agent_type}"
    
    async def _process_query(self, query: str, prompt_type: str) -> Dict[str, Any]:
        """Process the query using the specified prompt type.
        
        Args:
            query: The user's query
            prompt_type: The type of prompt to use
            
        Returns:
            Dictionary containing the response and metadata
        """
        try:
            # Get the appropriate prompt
            prompt = self.get_prompt(prompt_type)
            
            # Process the query using Azure OpenAI
            completion = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {{"role": "system", "content": prompt}},
                    {{"role": "user", "content": query}}
                ]
            )
            
            # Extract and format the response
            response = completion.choices[0].message.content
            
            return {{
                "status": "success",
                "response": {{
                    "content": response,
                    "metadata": {{
                        "prompt_type": prompt_type,
                        "agent_type": self.agent_type
                    }}
                }}
            }}
            
        except Exception as e:
            return {{
                "status": "error",
                "error": str(e)
            }}
'''

def create_prompt_file(agent_type: str, prompt_type: str) -> str:
    """Generate the prompt file content."""
    return f'''# Role and Purpose
You are a {agent_type.replace('_', ' ').title()} assistant. Your purpose is to handle {prompt_type.replace('_', ' ')} related queries.

# Guidelines
- Be clear and concise in your responses
- Provide relevant examples when appropriate
- Maintain a professional and helpful tone
- Focus on accuracy and completeness

# Examples
Example 1: [Add example query and response]
Example 2: [Add example query and response]

# Error Handling
- If the query is unclear, ask for clarification
- If the query is out of scope, explain the limitations
- If an error occurs, provide a helpful error message
'''

def create_test_file(agent_name: str) -> str:
    """Generate the test file content."""
    class_name = ''.join(word.capitalize() for word in agent_name.split('_'))
    
    return f'''import pytest
from unittest.mock import Mock, patch
from app.modules.semantic_kernel.agents.{agent_name} import {class_name}
from app.core.config.settings import Settings

@pytest.fixture
def agent():
    settings = Settings()
    return {class_name}(settings)

@pytest.mark.asyncio
async def test_process_query_success(agent):
    # Arrange
    query = "Test query"
    prompt_type = "general"
    
    # Mock the Azure OpenAI client
    with patch.object(agent.client.chat.completions, 'create') as mock_create:
        mock_create.return_value.choices = [
            Mock(message=Mock(content="Test response"))
        ]
        
        # Act
        result = await agent._process_query(query, prompt_type)
        
        # Assert
        assert result["status"] == "success"
        assert "content" in result["response"]
        assert result["response"]["metadata"]["prompt_type"] == prompt_type

@pytest.mark.asyncio
async def test_process_query_error(agent):
    # Arrange
    query = "Test query"
    prompt_type = "general"
    
    # Mock the Azure OpenAI client to raise an exception
    with patch.object(agent.client.chat.completions, 'create') as mock_create:
        mock_create.side_effect = Exception("Test error")
        
        # Act
        result = await agent._process_query(query, prompt_type)
        
        # Assert
        assert result["status"] == "error"
        assert "error" in result
'''

def update_agent_registry(agent_name: str, prompt_types: List[str]) -> str:
    """Generate the agent registry update code."""
    class_name = ''.join(word.capitalize() for word in agent_name.split('_'))
    agent_type = agent_name.lower()
    
    return f'''
# Add to _agent_classes dictionary
"{agent_type}": {{
    "class": {class_name},
    "name": "{class_name}",
    "description": "Handles {agent_type.replace('_', ' ')} related queries"
}},

# Add to _agent_prompt_types dictionary
"{agent_type}": {prompt_types},
'''

def main():
    parser = argparse.ArgumentParser(description='Create a new agent for Maarefa Agent V2')
    parser.add_argument('agent_name', help='Name of the agent (e.g., study_guide)')
    parser.add_argument('--prompt-types', nargs='+', default=['general'],
                      help='List of prompt types for the agent')
    
    args = parser.parse_args()
    
    # Convert agent name to proper format
    agent_name = args.agent_name.lower().replace(' ', '_')
    prompt_types = [pt.lower().replace(' ', '_') for pt in args.prompt_types]
    
    # Create necessary directories
    base_dir = Path('app/modules/semantic_kernel')
    agent_dir = base_dir / 'agents'
    prompt_dir = base_dir / 'prompts' / agent_name
    test_dir = Path('tests/unit/agents')
    
    agent_dir.mkdir(parents=True, exist_ok=True)
    prompt_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create agent class file
    agent_file = agent_dir / f'{agent_name}.py'
    with open(agent_file, 'w') as f:
        f.write(create_agent_class(agent_name, prompt_types))
    
    # Create prompt files
    for prompt_type in prompt_types:
        prompt_file = prompt_dir / f'{prompt_type}.prompty'
        with open(prompt_file, 'w') as f:
            f.write(create_prompt_file(agent_name, prompt_type))
    
    # Create test file
    test_file = test_dir / f'test_{agent_name}.py'
    with open(test_file, 'w') as f:
        f.write(create_test_file(agent_name))
    
    # Print registry update instructions
    print("\nAdd the following to app/modules/semantic_kernel/registry/agent_registry.py:")
    print(update_agent_registry(agent_name, prompt_types))
    
    print(f"\nAgent '{agent_name}' created successfully!")
    print(f"Files created:")
    print(f"- {agent_file}")
    print(f"- {prompt_dir}/")
    print(f"- {test_file}")
    print("\nDon't forget to:")
    print("1. Update the agent registry with the provided code")
    print("2. Add your agent to the imports in __init__.py")
    print("3. Create appropriate prompts in the prompt files")
    print("4. Write additional tests as needed")

if __name__ == '__main__':
    main() 