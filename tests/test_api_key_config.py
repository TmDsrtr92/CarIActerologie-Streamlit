"""
Tests for API key configuration loading
"""

import pytest
from unittest.mock import patch
from infrastructure.config.settings import get_config, get_openai_api_key, reload_config


class TestAPIKeyConfiguration:
    """Test API key configuration loading"""
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test-fake-key-for-testing'})
    def test_api_key_loaded_from_environment(self):
        """Test that API key is properly loaded from environment variables"""
        # Reload config to ensure fresh state
        config = reload_config()
        
        # Test that API key is loaded from environment when secrets not available
        api_key = get_openai_api_key()
        assert api_key is not None
        assert len(api_key) > 0
        assert api_key == "sk-test-fake-key-for-testing"
    
    def test_config_has_proper_llm_model_attribute(self):
        """Test that LLM config has the model attribute (not just model_name)"""
        config = get_config()
        
        # Test that LLM config exists and has required attributes
        assert hasattr(config, 'llm')
        assert hasattr(config.llm, 'model')
        assert hasattr(config.llm, 'model_name')
        assert config.llm.model is not None
        assert config.llm.model_name is not None
        
        # Test that model and model_name return the same value
        assert config.llm.model == config.llm.model_name
    
    def test_development_config_inherits_api_settings(self):
        """Test that development config properly inherits API settings"""
        from infrastructure.config.environments.development import get_development_config
        
        dev_config = get_development_config()
        
        # Test that development config has API settings
        assert hasattr(dev_config, 'api')
        assert hasattr(dev_config.api, 'openai_api_key')
        assert dev_config.api.openai_api_key is not None
        assert len(dev_config.api.openai_api_key) > 0
        
        # Test environment-specific overrides
        assert dev_config.environment == "development"
        assert dev_config.debug is True
        assert dev_config.logging.level == "DEBUG"
    
    @patch.dict('os.environ', {'APP_ENV': 'development'})
    def test_environment_config_selection(self):
        """Test that the correct environment config is selected"""
        # Clear any cached config
        config = reload_config()
        
        # Should load development config
        assert config.environment == "development"
        assert config.debug is True
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test-fake-key-for-testing'})
    def test_llm_client_can_initialize_with_api_key(self):
        """Test that LLM client can initialize with the loaded API key"""
        from services.ai_service.llm_client import get_llm_client
        
        # Reload config to use test API key
        reload_config()
        
        # This should not raise any errors
        llm_client = get_llm_client()
        assert llm_client is not None
        
        # This should initialize the LLM without errors (even with fake key for testing structure)
        try:
            llm = llm_client.get_llm()
            assert llm is not None
            assert hasattr(llm, 'model_name')
        except Exception as e:
            # In test environment, we just want to verify the config structure works
            # Actual API calls may fail with fake keys, which is expected
            assert "api" in str(e).lower() or "auth" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__])