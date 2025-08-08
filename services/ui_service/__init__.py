"""
UI service - handles user interface components and interactions.
"""

from .chunks_renderer import ChunksRenderer, ChunksCollector, get_chunks_renderer

# Lazy import to avoid circular dependency with core.callbacks
def get_chat_interface():
    from .chat_interface import get_chat_interface as _get_chat_interface
    return _get_chat_interface()

def get_chat_interface_class():
    from .chat_interface import ChatInterface
    return ChatInterface

__all__ = [
    'ChunksRenderer', 
    'ChunksCollector', 
    'get_chunks_renderer',
    'get_chat_interface',
    'get_chat_interface_class'
]