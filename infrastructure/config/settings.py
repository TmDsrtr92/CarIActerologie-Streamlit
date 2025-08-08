"""
Unified Configuration System for CarIActérologie
Refactored into infrastructure layer for microservices architecture.

This module provides a centralized configuration system that consolidates all application settings,
supports environment-based overrides, and provides type-safe configuration access.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import streamlit as st
import os
from pathlib import Path


@dataclass
class APIConfig:
    """API configuration settings"""
    openai_api_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    
    @classmethod
    def from_secrets(cls) -> 'APIConfig':
        """Load API config from Streamlit secrets"""
        # In test environment, prefer environment variables
        if os.getenv("PYTEST_CURRENT_TEST") is not None:
            return cls(
                openai_api_key=os.getenv("OPENAI_API_KEY", ""),
                langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
                langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
                langfuse_host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
            )
        
        try:
            return cls(
                openai_api_key=st.secrets.get("OPENAI_API_KEY", ""),
                langfuse_secret_key=st.secrets.get("LANGFUSE_SECRET_KEY", ""),
                langfuse_public_key=st.secrets.get("LANGFUSE_PUBLIC_KEY", ""),
                langfuse_host=st.secrets.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
            )
        except Exception:
            # Fallback to environment variables if secrets not available
            return cls(
                openai_api_key=os.getenv("OPENAI_API_KEY", ""),
                langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
                langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
                langfuse_host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
            )


@dataclass
class LLMConfig:
    """Language model configuration"""
    model: str = "gpt-4o-mini"  # Updated field name for consistency
    temperature: float = 0.5
    max_tokens: int = 1000
    streaming: bool = True
    embedding_model: str = "text-embedding-3-small"
    
    # Keep model_name for backward compatibility
    @property
    def model_name(self) -> str:
        return self.model
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LangChain compatibility"""
        return {
            "model_name": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "streaming": self.streaming
        }


@dataclass
class VectorStoreCollection:
    """Vector store collection configuration"""
    collection_name: str
    description: str
    chunk_type: str  # "semantic" or "character"
    store_type: str = "faiss"  # "faiss" or "chroma"
    search_kwargs: Dict[str, Any] = field(default_factory=lambda: {"k": 5})


@dataclass
class VectorStoreConfig:
    """Vector store configuration"""
    persist_directory: str = "./infrastructure/database/vectorstores"
    search_kwargs: Dict[str, Any] = field(default_factory=lambda: {"k": 10})
    
    # Available collections
    collections: Dict[str, VectorStoreCollection] = field(default_factory=lambda: {
        "subchapters": VectorStoreCollection(
            collection_name="traite_subchapters_faiss",
            description="FAISS chunks based on document sub-chapters (~336 semantic chunks)",
            chunk_type="semantic",
            store_type="faiss"
        ),
        "original": VectorStoreCollection(
            collection_name="traite_faiss",
            description="FAISS character-based chunks (~2800 small chunks)",
            chunk_type="character",
            store_type="faiss"
        )
    })
    
    default_collection_key: str = "subchapters"
    
    def get_collection_config(self, collection_key: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for specific collection"""
        if collection_key is None:
            collection_key = self.default_collection_key
        
        if collection_key not in self.collections:
            collection_key = self.default_collection_key
        
        collection = self.collections[collection_key]
        
        return {
            "persist_directory": self.persist_directory,
            "collection_name": collection.collection_name,
            "search_kwargs": collection.search_kwargs,
            "description": collection.description,
            "chunk_type": collection.chunk_type,
            "store_type": collection.store_type
        }


@dataclass
class MemoryConfig:
    """Memory management configuration"""
    max_token_limit: int = 4000
    model_name: str = "gpt-4o-mini"  # For token counting


@dataclass
class LangGraphConfig:
    """LangGraph memory configuration"""
    db_path: str = "infrastructure/database/conversations/conversations.db"
    enable_conversation_persistence: bool = True
    max_conversations: int = 50
    auto_summarize_old_conversations: bool = True
    summarize_threshold_days: int = 30
    enable_conversation_branching: bool = False
    enable_semantic_search: bool = False


@dataclass
class StreamingConfig:
    """Streaming response configuration"""
    update_every: int = 1
    delay: float = 0.01


@dataclass
class UIConfig:
    """User interface configuration"""
    app_title: str = "CarIActérologie"
    welcome_message: str = """👋 **Bienvenue dans CarIActérologie !**

Je suis votre assistant expert en caractérologie, spécialisé dans les travaux de René Le Senne. Je suis là pour vous accompagner dans la découverte de la science des types de caractère.

Que vous soyez novice ou déjà initié, je peux vous aider à :
- **Comprendre les fondements** de la caractérologie
- **Explorer votre type de caractère** et ses spécificités  
- **Approfondir vos connaissances** sur les 8 types caractérologiques
- **Appliquer ces concepts** dans votre développement personnel

Pour commencer, vous pouvez choisir une des suggestions ci-dessous ou me poser directement votre question :"""
    
    templated_prompts: List[Dict[str, str]] = field(default_factory=lambda: [
        {
            "id": "beginner",
            "title": "🌱 Débutant",
            "prompt": "Qu'est-ce que la caractérologie et comment peut-elle m'aider ?",
            "description": "Découvrir les bases de la caractérologie",
            "icon": "🌱"
        },
        {
            "id": "practical", 
            "title": "🔍 Pratique",
            "prompt": "Pouvez-vous m'aider à comprendre mon type de caractère ?",
            "description": "Analyse personnalisée de votre caractère",
            "icon": "🔍"
        },
        {
            "id": "advanced",
            "title": "📚 Expert",
            "prompt": "Expliquez-moi les nuances entre les types émotifs primaires et secondaires",
            "description": "Approfondissement théorique",
            "icon": "📚"
        }
    ])


@dataclass
class LoggingConfig:
    """Logging and monitoring configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_file_logging: bool = True
    log_file: str = "logs/app.log"
    enable_langfuse_tracing: bool = True


@dataclass
class AppConfig:
    """Main application configuration"""
    api: APIConfig = field(default_factory=APIConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    vectorstore: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    langgraph: LangGraphConfig = field(default_factory=LangGraphConfig)
    streaming: StreamingConfig = field(default_factory=StreamingConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    # Removed AuthConfig - using simple session-based user tracking
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Environment settings
    environment: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    
    @classmethod
    def load(cls) -> 'AppConfig':
        """Load configuration with environment overrides"""
        config = cls()
        
        # Load API configuration from secrets/environment
        config.api = APIConfig.from_secrets()
        
        # Apply environment-specific overrides
        if config.environment == "production":
            config.debug = False
            config.logging.level = "WARNING"
            config.langgraph.enable_conversation_branching = False
        elif config.environment == "development":
            config.debug = True
            config.logging.level = "DEBUG"
        
        return config
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Check required API keys
        if not self.api.openai_api_key:
            errors.append("OpenAI API key is required")
        
        # Check file paths exist
        if not Path(self.langgraph.db_path).parent.exists():
            Path(self.langgraph.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        if self.logging.enable_file_logging:
            log_dir = Path(self.logging.log_file).parent
            if not log_dir.exists():
                log_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate collection configurations
        for key, collection in self.vectorstore.collections.items():
            if not collection.collection_name:
                errors.append(f"Collection '{key}' missing collection_name")
        
        return errors
    
    def get_langfuse_config(self) -> Dict[str, str]:
        """Get Langfuse configuration for backward compatibility"""
        return {
            "secret_key": self.api.langfuse_secret_key,
            "public_key": self.api.langfuse_public_key,
            "host": self.api.langfuse_host
        }


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance with environment-specific overrides"""
    global _config
    if _config is None:
        # Always use base config for now to avoid environment-specific loading issues
        _config = AppConfig.load()
        
        # Validate configuration
        errors = _config.validate()
        if errors:
            import warnings
            for error in errors:
                warnings.warn(f"Configuration error: {error}")
    
    return _config


def reload_config() -> AppConfig:
    """Reload configuration (useful for testing)"""
    global _config
    _config = None
    return get_config()


# Backward compatibility functions
def get_openai_api_key() -> str:
    """Get OpenAI API key (backward compatibility)"""
    return get_config().api.openai_api_key


def get_langfuse_config() -> Dict[str, str]:
    """Get Langfuse configuration (backward compatibility)"""
    return get_config().get_langfuse_config()


def get_vectorstore_config(collection_key: Optional[str] = None) -> Dict[str, Any]:
    """Get vectorstore config for specified collection (backward compatibility)"""
    return get_config().vectorstore.get_collection_config(collection_key)