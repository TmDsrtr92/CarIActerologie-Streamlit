"""
Tests for configuration system
"""

import pytest
import os
import tempfile
from pathlib import Path
from config.app_config import (
    AppConfig, APIConfig, LLMConfig, VectorStoreConfig, 
    MemoryConfig, LangGraphConfig, StreamingConfig, UIConfig,
    get_config, reload_config
)


class TestAPIConfig:
    """Test API configuration"""
    
    def test_from_secrets_fallback_to_env(self, monkeypatch):
        """Test fallback to environment variables when secrets unavailable"""
        # Mock environment variables
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-langfuse-secret")
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-langfuse-public")
        
        config = APIConfig.from_secrets()
        
        assert config.openai_api_key == "test-openai-key"
        assert config.langfuse_secret_key == "test-langfuse-secret"
        assert config.langfuse_public_key == "test-langfuse-public"
        assert config.langfuse_host == "https://cloud.langfuse.com"


class TestLLMConfig:
    """Test LLM configuration"""
    
    def test_default_values(self):
        """Test default configuration values"""
        config = LLMConfig()
        
        assert config.model_name == "gpt-4o-mini"
        assert config.temperature == 0.5
        assert config.max_tokens == 1000
        assert config.streaming is True
    
    def test_to_dict(self):
        """Test conversion to dictionary"""
        config = LLMConfig()
        config_dict = config.to_dict()
        
        expected = {
            "model_name": "gpt-4o-mini",
            "temperature": 0.5,
            "max_tokens": 1000,
            "streaming": True
        }
        assert config_dict == expected


class TestVectorStoreConfig:
    """Test vector store configuration"""
    
    def test_default_collections(self):
        """Test default collections are properly configured"""
        config = VectorStoreConfig()
        
        assert "Sub-chapters (Semantic)" in config.collections
        assert "Original (Character-based)" in config.collections
        assert config.default_collection_key == "Sub-chapters (Semantic)"
    
    def test_get_collection_config_default(self):
        """Test getting default collection config"""
        config = VectorStoreConfig()
        collection_config = config.get_collection_config()
        
        assert collection_config["collection_name"] == "traite_subchapters"
        assert collection_config["chunk_type"] == "semantic"
        assert collection_config["search_kwargs"] == {"k": 10}
    
    def test_get_collection_config_specific(self):
        """Test getting specific collection config"""
        config = VectorStoreConfig()
        collection_config = config.get_collection_config("Original (Character-based)")
        
        assert collection_config["collection_name"] == "traite"
        assert collection_config["chunk_type"] == "character"
    
    def test_get_collection_config_invalid_fallback(self):
        """Test fallback to default for invalid collection key"""
        config = VectorStoreConfig()
        collection_config = config.get_collection_config("NonExistent")
        
        # Should fallback to default
        assert collection_config["collection_name"] == "traite_subchapters"


class TestAppConfig:
    """Test main application configuration"""
    
    def test_default_initialization(self):
        """Test default configuration initialization"""
        config = AppConfig()
        
        assert isinstance(config.api, APIConfig)
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.vectorstore, VectorStoreConfig)
        assert isinstance(config.memory, MemoryConfig)
        assert isinstance(config.langgraph, LangGraphConfig)
        assert isinstance(config.streaming, StreamingConfig)
        assert isinstance(config.ui, UIConfig)
    
    def test_environment_detection(self, monkeypatch):
        """Test environment detection"""
        monkeypatch.setenv("APP_ENV", "production")
        config = AppConfig()
        assert config.environment == "production"
        
        monkeypatch.setenv("APP_ENV", "development")
        config = AppConfig()
        assert config.environment == "development"
    
    def test_debug_flag(self, monkeypatch):
        """Test debug flag configuration"""
        monkeypatch.setenv("DEBUG", "true")
        config = AppConfig()
        assert config.debug is True
        
        monkeypatch.setenv("DEBUG", "false")
        config = AppConfig()
        assert config.debug is False
    
    def test_production_overrides(self, monkeypatch):
        """Test production environment overrides"""
        monkeypatch.setenv("APP_ENV", "production")
        config = AppConfig.load()
        
        assert config.debug is False
        assert config.logging.level == "WARNING"
        assert config.langgraph.enable_conversation_branching is False
    
    def test_development_overrides(self, monkeypatch):
        """Test development environment overrides"""
        monkeypatch.setenv("APP_ENV", "development")
        config = AppConfig.load()
        
        assert config.debug is True
        assert config.logging.level == "DEBUG"
    
    def test_validate_missing_api_key(self):
        """Test validation catches missing API key"""
        config = AppConfig()
        config.api.openai_api_key = ""
        
        errors = config.validate()
        assert "OpenAI API key is required" in errors
    
    def test_validate_creates_directories(self):
        """Test validation creates necessary directories"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = AppConfig()
            config.langgraph.db_path = os.path.join(temp_dir, "subdir", "test.db")
            config.logging.log_file = os.path.join(temp_dir, "logs", "test.log")
            config.logging.enable_file_logging = True
            
            config.validate()
            
            assert Path(temp_dir, "subdir").exists()
            assert Path(temp_dir, "logs").exists()
    
    def test_get_langfuse_config(self):
        """Test Langfuse configuration dictionary"""
        config = AppConfig()
        config.api.langfuse_secret_key = "test-secret"
        config.api.langfuse_public_key = "test-public"
        config.api.langfuse_host = "test-host"
        
        langfuse_config = config.get_langfuse_config()
        
        expected = {
            "secret_key": "test-secret",
            "public_key": "test-public",
            "host": "test-host"
        }
        assert langfuse_config == expected


class TestConfigSingleton:
    """Test configuration singleton behavior"""
    
    def test_get_config_singleton(self):
        """Test that get_config returns the same instance"""
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
    
    def test_reload_config(self):
        """Test configuration reloading"""
        config1 = get_config()
        config2 = reload_config()
        
        # Should be different instances after reload
        assert config1 is not config2
        assert isinstance(config2, AppConfig)


class TestBackwardCompatibility:
    """Test backward compatibility functions"""
    
    def test_get_openai_api_key(self, monkeypatch):
        """Test backward compatibility for OpenAI API key"""
        from config.app_config import get_openai_api_key
        
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        reload_config()  # Reload to pick up env var
        
        api_key = get_openai_api_key()
        assert api_key == "test-key"
    
    def test_get_langfuse_config_compat(self, monkeypatch):
        """Test backward compatibility for Langfuse config"""
        from config.app_config import get_langfuse_config
        
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "test-secret")
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "test-public")
        reload_config()
        
        langfuse_config = get_langfuse_config()
        assert langfuse_config["secret_key"] == "test-secret"
        assert langfuse_config["public_key"] == "test-public"
    
    def test_get_vectorstore_config_compat(self):
        """Test backward compatibility for vectorstore config"""
        from config.app_config import get_vectorstore_config
        
        config = get_vectorstore_config()
        assert "collection_name" in config
        assert "persist_directory" in config
        assert "search_kwargs" in config
        assert "description" in config
        assert "chunk_type" in config


if __name__ == "__main__":
    pytest.main([__file__])