"""
LLM client - handles LLM setup and interactions.
Refactored from core/llm_setup.py into a service-oriented architecture.
"""

from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma, FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.retrievers import BaseRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from typing import Optional

from infrastructure.config.settings import get_openai_api_key, get_config
from infrastructure.monitoring.logging_service import get_logger


class LLMClient:
    """
    Client for LLM interactions and setup.
    Handles ChatOpenAI initialization and configuration.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self._llm = None
    
    def get_llm(self) -> ChatOpenAI:
        """
        Get configured ChatOpenAI instance
        
        Returns:
            Configured ChatOpenAI instance
        """
        if self._llm is None:
            try:
                api_key = get_openai_api_key()
                if not api_key:
                    raise ValueError("OpenAI API key not configured")
                
                self._llm = ChatOpenAI(
                    model=self.config.llm.model,
                    temperature=self.config.llm.temperature,
                    max_tokens=self.config.llm.max_tokens,
                    openai_api_key=api_key,
                    streaming=self.config.llm.streaming
                )
                
                self.logger.info(f"LLM initialized: {self.config.llm.model}")
                
            except Exception as e:
                self.logger.error(f"Error initializing LLM: {e}")
                raise
        
        return self._llm
    
    def get_embeddings(self) -> OpenAIEmbeddings:
        """
        Get OpenAI embeddings instance
        
        Returns:
            Configured OpenAIEmbeddings instance
        """
        try:
            api_key = get_openai_api_key()
            if not api_key:
                raise ValueError("OpenAI API key not configured")
            
            embeddings = OpenAIEmbeddings(
                model=self.config.llm.embedding_model,
                openai_api_key=api_key
            )
            
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Error initializing embeddings: {e}")
            raise


class VectorStoreClient:
    """
    Client for vector store operations and retrieval.
    Handles vector store setup and retriever creation.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.llm_client = LLMClient()
    
    def get_retriever(self, collection_key: str = None) -> BaseRetriever:
        """
        Get retriever for specified collection
        
        Args:
            collection_key: Key for the collection to use
            
        Returns:
            Configured retriever instance
        """
        try:
            if collection_key is None:
                collection_key = self.config.vectorstore.default_collection_key
            
            if collection_key not in self.config.vectorstore.collections:
                raise ValueError(f"Collection not found: {collection_key}")
            
            collection_config = self.config.vectorstore.collections[collection_key]
            
            if collection_config.store_type == "chroma":
                return self._get_chroma_retriever(collection_config)
            elif collection_config.store_type == "faiss":
                return self._get_faiss_retriever(collection_config)
            else:
                raise ValueError(f"Unsupported store type: {collection_config.store_type}")
            
        except Exception as e:
            self.logger.error(f"Error getting retriever: {e}")
            raise
    
    def _get_chroma_retriever(self, collection_config) -> BaseRetriever:
        """Get Chroma-based retriever"""
        try:
            embeddings = self.llm_client.get_embeddings()
            
            # Initialize Chroma
            vectorstore = Chroma(
                collection_name=collection_config.collection_name,
                embedding_function=embeddings,
                persist_directory="infrastructure/database/vectorstores"
            )
            
            # Create retriever with search configuration
            retriever = vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={
                    "k": collection_config.search_kwargs.get("k", 5)
                }
            )
            
            self.logger.info(f"Chroma retriever initialized: {collection_config.collection_name}")
            return retriever
            
        except Exception as e:
            self.logger.error(f"Error initializing Chroma retriever: {e}")
            raise
    
    def _get_faiss_retriever(self, collection_config) -> BaseRetriever:
        """Get FAISS-based retriever"""
        try:
            embeddings = self.llm_client.get_embeddings()
            
            # Load FAISS index
            faiss_path = f"infrastructure/database/vectorstores/{collection_config.collection_name}"
            if not os.path.exists(f"{faiss_path}/index.faiss"):
                raise FileNotFoundError(f"FAISS index not found: {faiss_path}")
            
            vectorstore = FAISS.load_local(
                faiss_path,
                embeddings,
                allow_dangerous_deserialization=True
            )
            
            # Create retriever with search configuration
            retriever = vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={
                    "k": collection_config.search_kwargs.get("k", 5)
                }
            )
            
            self.logger.info(f"FAISS retriever initialized: {collection_config.collection_name}")
            return retriever
            
        except Exception as e:
            self.logger.error(f"Error initializing FAISS retriever: {e}")
            raise


# Global client instances
_llm_client: Optional[LLMClient] = None
_vectorstore_client: Optional[VectorStoreClient] = None


def get_llm_client() -> LLMClient:
    """Get the global LLM client instance"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def get_vectorstore_client() -> VectorStoreClient:
    """Get the global vector store client instance"""
    global _vectorstore_client
    if _vectorstore_client is None:
        _vectorstore_client = VectorStoreClient()
    return _vectorstore_client


# Legacy compatibility functions
def setup_llm() -> ChatOpenAI:
    """Setup LLM (legacy compatibility)"""
    client = get_llm_client()
    return client.get_llm()


def setup_retriever(collection_key: str = None) -> BaseRetriever:
    """Setup retriever (legacy compatibility)"""
    client = get_vectorstore_client()
    return client.get_retriever(collection_key)