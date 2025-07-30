from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from functools import lru_cache
from dotenv import load_dotenv
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Log environment variables for debugging
logger.info(f"MONGODB_URL from env: {os.getenv('MONGODB_URL')}")
logger.info(f"MONGODB_DB_NAME from env: {os.getenv('MONGODB_DB_NAME')}")

class Settings(BaseSettings):
    """Application settings."""
    
    # MongoDB Configuration
    MONGODB_URL: str = "mongodb://mongodb:27017"  # Hardcoded for Docker
    MONGODB_DB_NAME: str = "tachriat_agent"  # Hardcoded
    
    # Azure OpenAI Configuration
    AZURE_OPENAI_DEPLOYMENT_NAME: str = Field(
        default=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", ""),
        description="Azure OpenAI deployment name"
    )
    AZURE_OPENAI_ENDPOINT: str = Field(
        default=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        description="Azure OpenAI endpoint URL"
    )
    AZURE_OPENAI_API_KEY: str = Field(
        default=os.getenv("AZURE_OPENAI_API_KEY", ""),
        description="Azure OpenAI API key"
    )
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME: str = Field(
        default=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", ""),
        description="Azure OpenAI embedding deployment name"
    )
    
    # Azure AI Search Configuration
    AZURE_AI_SEARCH_ENDPOINT: str = Field(
        default=os.getenv("AZURE_AI_SEARCH_ENDPOINT", ""),
        description="Azure AI Search endpoint URL"
    )
    AZURE_AI_SEARCH_API_KEY: str = Field(
        default=os.getenv("AZURE_AI_SEARCH_API_KEY", ""),
        description="Azure AI Search API key"
    )
    AZURE_AI_SEARCH_STUDY_INDEX_NAME: str = Field(
        default=os.getenv("AZURE_AI_SEARCH_STUDY_INDEX_NAME", ""),
        description="Azure AI Search index name for the Study Agent"
    )
    
    # Azure AI Search Configuration
    AZURE_AI_SEARCH_ENDPOINT: str = Field(
        default=os.getenv("AZURE_AI_SEARCH_ENDPOINT", ""),
        description="Azure AI Search endpoint URL"
    )
    AZURE_AI_SEARCH_API_KEY: str = Field(
        default=os.getenv("AZURE_AI_SEARCH_API_KEY", ""),
        description="Azure AI Search API key"
    )
    
    # Application Configuration
    APP_ENV: str = Field(
        default=os.getenv("APP_ENV", "development"),
        description="Application environment"
    )
    PORT: int = Field(
        default=int(os.getenv("PORT", "8000")),
        description="Application port"
    )
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info(f"Initialized Settings with MONGODB_URL: {self.MONGODB_URL}")
        logger.info(f"Initialized Settings with MONGODB_DB_NAME: {self.MONGODB_DB_NAME}")

# Create a global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings 