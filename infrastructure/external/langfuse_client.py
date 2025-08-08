"""
Langfuse client adapter for the application.
Handles Langfuse integration for observability and prompt management.
"""

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from typing import Optional
import streamlit as st

from infrastructure.config.settings import get_config, get_langfuse_config
from infrastructure.monitoring.logging_service import get_logger


class LangfuseClient:
    """
    Adapter for Langfuse observability and prompt management.
    Provides centralized access to Langfuse services.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self._client = None
        self._callback_handler = None
    
    def get_client(self) -> Optional[Langfuse]:
        """
        Get configured Langfuse client
        
        Returns:
            Optional[Langfuse]: Configured client or None if not available
        """
        if self._client is None:
            try:
                langfuse_config = get_langfuse_config()
                
                # Check if keys are available
                if not langfuse_config["secret_key"] or not langfuse_config["public_key"]:
                    self.logger.debug("Langfuse keys not configured, skipping initialization")
                    return None
                
                self._client = Langfuse(
                    secret_key=langfuse_config["secret_key"],
                    public_key=langfuse_config["public_key"],
                    host=langfuse_config["host"]
                )
                
                self.logger.info("Langfuse client initialized successfully")
                
            except Exception as e:
                self.logger.warning(f"Failed to initialize Langfuse client: {e}")
                return None
        
        return self._client
    
    def get_callback_handler(self) -> Optional[CallbackHandler]:
        """
        Get Langfuse callback handler for LangChain integration
        
        Returns:
            Optional[CallbackHandler]: Callback handler or None if not available
        """
        if self._callback_handler is None:
            try:
                client = self.get_client()
                if client is None:
                    return None
                
                self._callback_handler = CallbackHandler()
                self.logger.debug("Langfuse callback handler created")
                
            except Exception as e:
                self.logger.warning(f"Failed to create Langfuse callback handler: {e}")
                return None
        
        return self._callback_handler
    
    def get_prompt(self, prompt_name: str, version: Optional[int] = None) -> Optional[str]:
        """
        Get prompt from Langfuse prompt management
        
        Args:
            prompt_name: Name of the prompt
            version: Specific version (optional)
            
        Returns:
            Optional[str]: Prompt content or None if not available
        """
        try:
            client = self.get_client()
            if client is None:
                return None
            
            if version:
                prompt = client.get_prompt(prompt_name, version=version)
            else:
                prompt = client.get_prompt(prompt_name)
            
            return prompt.prompt
            
        except Exception as e:
            self.logger.warning(f"Failed to get prompt '{prompt_name}': {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test connection to Langfuse
        
        Returns:
            bool: True if connection successful
        """
        try:
            client = self.get_client()
            if client is None:
                return False
            
            # Test by trying to get a prompt (this will validate the connection)
            # We don't care if the prompt exists, just that we can connect
            try:
                client.get_prompt("test_connection_prompt")
            except Exception:
                # Expected if prompt doesn't exist, but connection works
                pass
            
            self.logger.info("Langfuse connection test successful")
            return True
            
        except Exception as e:
            self.logger.warning(f"Langfuse connection test failed: {e}")
            return False


# Global client instance
_langfuse_client: Optional[LangfuseClient] = None


def get_langfuse_client() -> LangfuseClient:
    """Get the global Langfuse client instance"""
    global _langfuse_client
    if _langfuse_client is None:
        _langfuse_client = LangfuseClient()
    return _langfuse_client