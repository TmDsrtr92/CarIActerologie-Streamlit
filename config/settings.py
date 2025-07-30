"""
Legacy settings module - now imports from unified configuration system.
This module is maintained for backward compatibility.
"""

import warnings
from config.app_config import (
    get_config,
    get_openai_api_key,
    get_langfuse_config, 
    get_vectorstore_config
)

# Issue deprecation warning
warnings.warn(
    "config.settings is deprecated. Use config.app_config instead.",
    DeprecationWarning,
    stacklevel=2
)

# Get configuration instance
_config = get_config()

# Backward compatibility exports
LLM_CONFIG = _config.llm.to_dict()
AVAILABLE_COLLECTIONS = {
    key: {
        "collection_name": collection.collection_name,
        "description": collection.description,
        "chunk_type": collection.chunk_type
    }
    for key, collection in _config.vectorstore.collections.items()
}
DEFAULT_COLLECTION_KEY = _config.vectorstore.default_collection_key
VECTORSTORE_CONFIG = get_vectorstore_config()
STREAMING_CONFIG = {
    "update_every": _config.streaming.update_every,
    "delay": _config.streaming.delay
}
MEMORY_CONFIG = {
    "max_token_limit": _config.memory.max_token_limit,
    "model_name": _config.memory.model_name
}
LANGGRAPH_MEMORY_CONFIG = {
    "db_path": _config.langgraph.db_path,
    "enable_conversation_persistence": _config.langgraph.enable_conversation_persistence,
    "max_conversations": _config.langgraph.max_conversations,
    "auto_summarize_old_conversations": _config.langgraph.auto_summarize_old_conversations,
    "summarize_threshold_days": _config.langgraph.summarize_threshold_days,
    "enable_conversation_branching": _config.langgraph.enable_conversation_branching,
    "enable_semantic_search": _config.langgraph.enable_semantic_search,
} 