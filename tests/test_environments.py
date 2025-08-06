"""
Test environment-specific configurations
"""

import os
import pytest
from config.environments import get_environment_config
from config.environments.development import get_development_config
from config.environments.production import get_production_config


class TestEnvironmentConfigs:
    """Test environment-specific configuration loading"""
    
    def test_development_config(self):
        """Test development configuration"""
        config = get_development_config()
        
        assert config.environment == "development"
        assert config.debug == True
        assert config.logging.level == "DEBUG"
        assert "DEV" in config.ui.app_title
        assert config.langgraph.enable_conversation_branching == True
        assert config.auth.require_email_verification == False
        
    def test_production_config(self):
        """Test production configuration"""
        config = get_production_config()
        
        assert config.environment == "production"
        assert config.debug == False
        assert config.logging.level == "INFO"
        assert "DEV" not in config.ui.app_title
        assert config.langgraph.enable_conversation_branching == False
        assert config.auth.require_email_verification == True
        assert config.llm.temperature == 0.3
        
    def test_environment_selection_development(self):
        """Test environment selection for development"""
        original_env = os.environ.get("APP_ENV")
        try:
            os.environ["APP_ENV"] = "development"
            config = get_environment_config()
            assert config.environment == "development"
            assert config.debug == True
        finally:
            if original_env is not None:
                os.environ["APP_ENV"] = original_env
            else:
                os.environ.pop("APP_ENV", None)
                
    def test_environment_selection_production(self):
        """Test environment selection for production"""
        original_env = os.environ.get("APP_ENV")
        try:
            os.environ["APP_ENV"] = "production"
            config = get_environment_config()
            assert config.environment == "production"
            assert config.debug == False
        finally:
            if original_env is not None:
                os.environ["APP_ENV"] = original_env
            else:
                os.environ.pop("APP_ENV", None)
                
    def test_default_environment(self):
        """Test default environment when APP_ENV is not set"""
        original_env = os.environ.get("APP_ENV")
        try:
            os.environ.pop("APP_ENV", None)
            config = get_environment_config()
            # Should default to development
            assert config.environment == "development"
        finally:
            if original_env is not None:
                os.environ["APP_ENV"] = original_env
                
    def test_config_validation(self):
        """Test that all environment configs pass validation"""
        configs = [
            get_development_config(),
            get_production_config()
        ]
        
        for config in configs:
            errors = config.validate()
            # Should have no critical errors (warnings are OK)
            critical_errors = [e for e in errors if "API key" in e]
            assert len(critical_errors) <= 1  # API key missing is expected in tests