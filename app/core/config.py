from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from typing import Optional

class Settings(BaseSettings):
    # MongoDB settings
    MONGODB_URL: str = Field(
        description="MongoDB connection URL",
        examples=["mongodb://localhost:27017"]
    )
    MONGODB_DB_NAME: str = Field(
        description="MongoDB database name",
        examples=["tachriat_agent"]
    )
    
    # App settings
    APP_ENV: str = Field(
        default="development",
        description="Application environment"
    )
    PORT: str = Field(
        default="8000",
        description="Application port"
    )
    
    # Azure OpenAI settings
    AZURE_OPENAI_DEPLOYMENT_NAME: str = Field(
        description="Azure OpenAI deployment name"
    )
    AZURE_OPENAI_ENDPOINT: str = Field(
        description="Azure OpenAI endpoint URL"
    )
    AZURE_OPENAI_API_KEY: str = Field(
        description="Azure OpenAI API key"
    )
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow",
        validate_default=True
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.MONGODB_URL:
            raise ValueError("MONGODB_URL must be set")
        if not self.MONGODB_DB_NAME:
            raise ValueError("MONGODB_DB_NAME must be set")

settings = Settings() 