"""Application settings loaded from environment variables"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union

class Settings(BaseSettings):
    """Application configuration settings"""

    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    PERSON_NAME: str
    KNOWLEDGE_BASE_PATH: str = "../data/knowledge_base.txt"
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173"

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, value):
        """Parse CORS_ORIGINS from string or list"""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(',')]
        return value

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
