"""
Configuration module for Alberta Perspectives RAG API
Manages environment variables and application settings.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Google AI Configuration
    gemini_api_key: str | None = None
    
    # Supabase Configuration
    supabase_url: str | None = None
    supabase_key: str | None = None
    
    # Application Configuration
    environment: str = "development"
    log_level: str = "INFO"
    
    # Processing Configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_tokens: int = 8192
    temperature: float = 0.7
    
    # Vector Search Configuration
    similarity_threshold: float = 0.75
    max_results: int = 5
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }
    
    @field_validator('gemini_api_key', 'supabase_url', 'supabase_key', mode="before", check_fields=False)
    @classmethod
    def warn_missing_fields(cls, v, field):
        if not v:
            logger.warning(f"Environment variable for '{field.name}' is not set. Some functionality may be limited.")
        return v
    
    @field_validator('supabase_url')
    @classmethod
    def validate_supabase_url(cls, v):
        if v and not v.startswith('https://'):
            logger.warning('Supabase URL should start with https://')
        return v

def get_settings() -> Settings:
    """Get application settings instance."""
    try:
        settings = Settings()
        logger.info(f"Configuration loaded successfully for environment: {settings.environment}")
        return settings
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        raise

# Global settings instance
settings = get_settings() 