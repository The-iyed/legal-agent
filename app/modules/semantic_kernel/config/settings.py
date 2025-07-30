from typing import Dict, Any
from ....core.config.settings import get_settings

class SemanticKernelSettings:
    """Settings for semantic kernel configuration."""
    
    @staticmethod
    def get_settings() -> Dict[str, Any]:
        """Get semantic kernel settings."""
        azure_settings = get_settings.get_azure_openai_settings()
        return {
            "deployment_name": azure_settings["deployment_name"],
            "endpoint": azure_settings["endpoint"],
            "api_key": azure_settings["api_key"],
            "api_version": "2024-02-15-preview",
            "max_tokens": 2000,
            "temperature": 0.7
        }

settings = SemanticKernelSettings.get_settings()