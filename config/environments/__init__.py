"""
Environment-specific configurations
"""

import os
from config.app_config import AppConfig


def get_environment_config() -> AppConfig:
    """
    Get configuration based on the current environment
    
    Environment is determined by APP_ENV environment variable:
    - 'development' -> DevelopmentConfig
    - 'production' -> ProductionConfig  
    - default -> AppConfig (base configuration)
    """
    
    env = os.getenv("APP_ENV", "development").lower()
    
    if env == "development":
        from .development import get_development_config
        return get_development_config()
    elif env == "production":
        from .production import get_production_config
        return get_production_config()
    else:
        # Default configuration for local development
        return AppConfig.load()