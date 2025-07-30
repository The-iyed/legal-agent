from typing import Dict, List, Optional
import os
from pathlib import Path
from ..semantic_kernel.registry.agent_registry import AgentRegistry
import yaml

class PromptManager:
    """Manager for handling prompts for different agents."""
    
    def __init__(self):
        """Initialize the prompt manager."""
        self.prompts_dir = Path(__file__).parent / "prompts"
        self.prompts: Dict[str, Dict[str, str]] = {}
        self._load_prompts()
    
    def _load_prompts(self):
        """Load all prompts from the prompts directory."""
        for agent_dir in self.prompts_dir.iterdir():
            if agent_dir.is_dir():
                agent_type = agent_dir.name
                self.prompts[agent_type] = {}
                
                for prompt_file in agent_dir.glob("*.prompty"):
                    prompt_type = prompt_file.stem
                    with open(prompt_file, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    
                    # Parse the .prompty file format
                    template = self._extract_template_from_prompty(content)
                    if template:
                        self.prompts[agent_type][prompt_type] = template
                    else:
                        # Fallback: use the entire content if parsing fails
                        self.prompts[agent_type][prompt_type] = content

    def _extract_template_from_prompty(self, content: str) -> Optional[str]:
        """Extract the template section from a .prompty file."""
        try:
            # Split content into lines
            lines = content.split('\n')
            
            # Find the template section
            template_start = -1
            for i, line in enumerate(lines):
                if line.strip().startswith('template:'):
                    template_start = i
                    break
            
            if template_start == -1:
                return None
            
            # Find the template_format line (end of template)
            template_end = len(lines)
            for i in range(template_start + 1, len(lines)):
                if lines[i].strip().startswith('template_format:'):
                    template_end = i
                    break
            
            # Extract template content (skip the "template: |" line)
            template_lines = lines[template_start + 1:template_end]
            
            # Remove the leading pipe and spaces from the first line if present
            if template_lines and template_lines[0].strip() == '|':
                template_lines = template_lines[1:]
            elif template_lines and template_lines[0].strip().startswith('|'):
                template_lines[0] = template_lines[0].replace('|', '', 1).lstrip()
            
            # Join the template lines
            template = '\n'.join(template_lines).strip()
            return template if template else None
            
        except Exception as e:
            print(f"Error parsing prompty file: {e}")
            return None
    
    def get_prompt(self, agent_type: str, prompt_type: str) -> Optional[str]:
        """
        Get a specific prompt for an agent.
        
        Args:
            agent_type: The type of agent
            prompt_type: The type of prompt
            
        Returns:
            The prompt text or None if not found
        """
        return self.prompts.get(agent_type, {}).get(prompt_type)
    
    def get_agent_prompts(self, agent_type: str) -> Dict[str, str]:
        """
        Get all prompts for an agent.
        
        Args:
            agent_type: The type of agent
            
        Returns:
            Dictionary of prompt types to prompt texts
        """
        return self.prompts.get(agent_type, {})
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agent types."""
        return list(self.prompts.keys())
    
    def get_available_prompt_types(self, agent_type: str) -> List[str]:
        """
        Get list of available prompt types for an agent.
        
        Args:
            agent_type: The type of agent
            
        Returns:
            List of available prompt types
        """
        return list(self.prompts.get(agent_type, {}).keys())
    
    def validate_agent_prompts(self, agent_type: str, required_prompt_types: List[str]) -> bool:
        """
        Validate that an agent has all required prompt types.
        
        Args:
            agent_type: The type of agent
            required_prompt_types: List of required prompt types
            
        Returns:
            True if all required prompts are available
        """
        available_prompts = self.get_available_prompt_types(agent_type)
        return all(prompt_type in available_prompts for prompt_type in required_prompt_types)
    
    @classmethod
    def get_available_prompts(cls, agent_type: str) -> Dict[str, str]:
        """Get all available prompts for an agent type."""
        if not cls.AGENT_PROMPTS:
            cls._load_prompts()
            
        if agent_type not in cls.AGENT_PROMPTS:
            raise ValueError(f"Unknown agent type: {agent_type}")
            
        return cls.AGENT_PROMPTS[agent_type]
    
    @classmethod
    def get_available_agent_types(cls) -> List[str]:
        """Get list of available agent types."""
        if not cls.AGENT_PROMPTS:
            cls._load_prompts()
            
        return list(cls.AGENT_PROMPTS.keys())
    
    @classmethod
    def validate_prompts(cls) -> None:
        """Validate that all registered agents have their prompts defined."""
        if not cls.AGENT_PROMPTS:
            cls._load_prompts()
            
        for agent_type in AgentRegistry.get_available_agents():
            if agent_type not in cls.AGENT_PROMPTS:
                raise ValueError(f"No prompts defined for agent type: {agent_type}")
            
            registry_prompt_types = AgentRegistry.get_agent_prompt_types(agent_type)
            defined_prompt_types = cls.AGENT_PROMPTS[agent_type].keys()
            
            missing_prompts = set(registry_prompt_types) - set(defined_prompt_types)
            if missing_prompts:
                raise ValueError(
                    f"Missing prompts for agent '{agent_type}': {', '.join(missing_prompts)}"
                ) 