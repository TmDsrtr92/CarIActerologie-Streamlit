"""
OpenAI client adapter for the application.
Handles OpenAI API interactions and configuration.
"""

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from typing import Optional
import openai

from infrastructure.config.settings import get_config, get_openai_api_key
from infrastructure.monitoring.logging_service import get_logger


class OpenAIClient:
    """
    Adapter for OpenAI services including ChatGPT and embeddings.
    Provides a centralized way to interact with OpenAI APIs.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self._chat_client = None
        self._embeddings_client = None
    
    def get_chat_client(self) -> ChatOpenAI:
        """
        Get configured ChatOpenAI client
        
        Returns:
            ChatOpenAI: Configured chat client
        """
        if self._chat_client is None:
            try:
                api_key = get_openai_api_key()
                if not api_key:
                    raise ValueError("OpenAI API key not configured")
                
                self._chat_client = ChatOpenAI(
                    model=self.config.llm.model,
                    temperature=self.config.llm.temperature,
                    max_tokens=self.config.llm.max_tokens,
                    openai_api_key=api_key,
                    streaming=self.config.llm.streaming
                )
                
                self.logger.info(f"OpenAI chat client initialized: {self.config.llm.model}")
                
            except Exception as e:
                self.logger.error(f"Error initializing OpenAI chat client: {e}")
                raise
        
        return self._chat_client
    
    def get_embeddings_client(self) -> OpenAIEmbeddings:
        """
        Get configured OpenAI embeddings client
        
        Returns:
            OpenAIEmbeddings: Configured embeddings client
        """
        if self._embeddings_client is None:
            try:
                api_key = get_openai_api_key()
                if not api_key:
                    raise ValueError("OpenAI API key not configured")
                
                self._embeddings_client = OpenAIEmbeddings(
                    model=self.config.llm.embedding_model,
                    openai_api_key=api_key
                )
                
                self.logger.info(f"OpenAI embeddings client initialized: {self.config.llm.embedding_model}")
                
            except Exception as e:
                self.logger.error(f"Error initializing OpenAI embeddings client: {e}")
                raise
        
        return self._embeddings_client
    
    def test_connection(self) -> bool:
        """
        Test connection to OpenAI API
        
        Returns:
            bool: True if connection successful
        """
        try:
            client = self.get_chat_client()
            # Simple test call
            response = client.invoke([{"role": "user", "content": "Test"}])
            self.logger.info("OpenAI connection test successful")
            return True
            
        except Exception as e:
            self.logger.error(f"OpenAI connection test failed: {e}")
            return False


# Global client instance
_openai_client: Optional[OpenAIClient] = None


def get_openai_client() -> OpenAIClient:
    """Get the global OpenAI client instance"""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAIClient()
    return _openai_client