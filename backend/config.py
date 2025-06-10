"""
Configuration module for Alberta Perspectives RAG API
Manages environment variables and application settings.
"""

import os
import logging

logger = logging.getLogger(__name__)

class Settings:
    """Simple application settings loaded from environment variables."""
    
    def __init__(self):
        # Google AI Configuration
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        # Supabase Configuration
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        # Application Configuration
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # Processing Configuration
        self.chunk_size = int(os.getenv('CHUNK_SIZE', '1000'))
        self.chunk_overlap = int(os.getenv('CHUNK_OVERLAP', '200'))
        self.max_tokens = int(os.getenv('MAX_TOKENS', '8192'))
        self.temperature = float(os.getenv('TEMPERATURE', '0.7'))
        
        # Vector Search Configuration
        self.similarity_threshold = float(os.getenv('SIMILARITY_THRESHOLD', '0.75'))
        self.max_results = int(os.getenv('MAX_RESULTS', '5'))
        
        # Log warnings for missing optional configs
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY not set. AI features will be limited.")
        if not self.supabase_url:
            logger.warning("SUPABASE_URL not set. Database features will be limited.")
        if not self.supabase_key:
            logger.warning("SUPABASE_KEY not set. Database features will be limited.")

def get_settings() -> Settings:
    """Get application settings instance."""
    try:
        settings = Settings()
        logger.info(f"Configuration loaded successfully for environment: {settings.environment}")
        return settings
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        # Return default settings even if there's an error
        settings = Settings()
        settings.gemini_api_key = None
        settings.supabase_url = None
        settings.supabase_key = None
        return settings

# Global settings instance
settings = get_settings() 