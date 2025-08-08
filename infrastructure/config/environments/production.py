"""
Production environment configuration overrides
Moved to infrastructure layer for microservices architecture.
"""

from dataclasses import dataclass, field
from infrastructure.config.settings import AppConfig, LLMConfig, VectorStoreConfig, LoggingConfig, UIConfig
from typing import Dict, Any, List


@dataclass
class ProductionConfig(AppConfig):
    """Production environment configuration"""
    
    def __post_init__(self):
        
        # Production-specific overrides
        self.environment = "production"
        self.debug = False
        
        # Production logging - less verbose, focus on errors
        self.logging.level = "INFO"
        self.logging.enable_file_logging = True
        self.logging.log_file = "logs/prod-app.log"
        
        # Production UI - clean and professional
        self.ui.app_title = "🧠 CarIActérologie"
        # Keep the original welcome message for production
        
        # Production-optimized settings
        self.langgraph.enable_conversation_branching = False
        self.langgraph.enable_semantic_search = False
        self.langgraph.max_conversations = 100  # Higher limit for production
        
        # Production security settings
        self.auth.allow_guest_mode = True
        self.auth.require_email_verification = True
        self.auth.max_login_attempts = 3
        self.auth.lockout_duration_minutes = 30
        
        # Production vector store settings - optimized for performance
        self.vectorstore.search_kwargs = {"k": 10}
        
        # Production LLM settings - more conservative
        self.llm.temperature = 0.3  # More consistent responses
        self.llm.max_tokens = 1000


def get_production_config() -> ProductionConfig:
    """Get production-specific configuration"""
    return ProductionConfig()