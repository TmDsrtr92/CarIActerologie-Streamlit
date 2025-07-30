import streamlit as st

# API Configuration
def get_openai_api_key():
    """Get OpenAI API key from Streamlit secrets"""
    return st.secrets["OPENAI_API_KEY"]

def get_langfuse_config():
    """Get Langfuse configuration from Streamlit secrets"""
    return {
        "secret_key": st.secrets["LANGFUSE_SECRET_KEY"],
        "public_key": st.secrets["LANGFUSE_PUBLIC_KEY"],
        "host": "https://cloud.langfuse.com"
    }

# Model Configuration
LLM_CONFIG = {
    "model_name": "gpt-4o-mini",
    "temperature": 0.5,
    "max_tokens": 1000,
    "streaming": True
}

# Available vectorstore collections
AVAILABLE_COLLECTIONS = {
    "Sub-chapters (Semantic)": {
        "collection_name": "traite_subchapters",
        "description": "Chunks based on document sub-chapters (~336 semantic chunks)",
        "chunk_type": "semantic"
    },
    "Original (Character-based)": {
        "collection_name": "traite",
        "description": "Original character-based chunks (~2800 small chunks)",
        "chunk_type": "character"
    }
}

# Default collection
DEFAULT_COLLECTION_KEY = "Sub-chapters (Semantic)"

# Vectorstore Configuration (dynamic)
def get_vectorstore_config(collection_key: str = None):
    """Get vectorstore config for specified collection"""
    if collection_key is None:
        collection_key = DEFAULT_COLLECTION_KEY
    
    if collection_key not in AVAILABLE_COLLECTIONS:
        collection_key = DEFAULT_COLLECTION_KEY
    
    collection_info = AVAILABLE_COLLECTIONS[collection_key]
    
    return {
        "persist_directory": "./index_stores",
        "collection_name": collection_info["collection_name"],
        "search_kwargs": {"k": 10},
        "description": collection_info["description"],
        "chunk_type": collection_info["chunk_type"]
    }

# Legacy config for backward compatibility
VECTORSTORE_CONFIG = get_vectorstore_config()

# Streaming Configuration
STREAMING_CONFIG = {
    "update_every": 3,
    "delay": 0.15
}

# Memory Configuration
MEMORY_CONFIG = {
    "max_token_limit": 4000,  # Maximum tokens to keep in conversation memory
    "model_name": "gpt-4o-mini"  # Model to use for token counting
}

# LangGraph Memory Configuration
LANGGRAPH_MEMORY_CONFIG = {
    "db_path": "conversations.db",  # SQLite database path for conversation persistence
    "enable_conversation_persistence": True,  # Enable conversation persistence across sessions
    "max_conversations": 50,  # Maximum number of conversations to keep
    "auto_summarize_old_conversations": True,  # Auto-summarize conversations older than threshold
    "summarize_threshold_days": 30,  # Days after which conversations are candidates for summarization
    "enable_conversation_branching": False,  # Enable conversation branching (future feature)
    "enable_semantic_search": False,  # Enable semantic search on conversation history (future feature)
} 