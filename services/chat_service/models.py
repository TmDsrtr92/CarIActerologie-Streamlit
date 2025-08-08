"""
Chat service data models for conversations and messages.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any


@dataclass
class Message:
    """Individual message in a conversation"""
    role: str  # "user", "assistant", "system"
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """Conversation containing messages and metadata"""
    conversation_id: str
    thread_id: str
    title: str
    messages: List[Message] = field(default_factory=list)
    welcome_shown: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationSummary:
    """Summary of conversation for listing/navigation"""
    conversation_id: str
    title: str
    message_count: int
    last_activity: datetime
    created_at: datetime
    preview_text: Optional[str] = None