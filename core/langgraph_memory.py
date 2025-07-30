from typing import Dict, Any, List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState
from langchain_openai import ChatOpenAI
import tiktoken
import sqlite3
import json
import os
from datetime import datetime
from config.settings import get_openai_api_key, MEMORY_CONFIG


class LangGraphMemoryManager:
    """
    LangGraph-based memory manager that replaces ConversationTokenBufferMemory
    with enhanced features for multi-conversation persistence and token management.
    """
    
    def __init__(self, max_token_limit: int = None, db_path: str = "conversations.db"):
        """
        Initialize LangGraph memory manager
        
        Args:
            max_token_limit: Maximum tokens to keep in memory
            db_path: Path to SQLite database for persistence
        """
        self.max_token_limit = max_token_limit or MEMORY_CONFIG["max_token_limit"]
        self.model_name = MEMORY_CONFIG["model_name"]
        self.db_path = db_path
        
        # Initialize tokenizer
        self.encoding = tiktoken.encoding_for_model(self.model_name)
        
        # Initialize simple in-memory storage for messages
        self._thread_messages = {}  # Simple dict storage: thread_id -> list of messages
        
        # Distinctive attribute to identify LangGraph memory manager
        self._is_langgraph_memory = True
        
        # Initialize database
        self._init_database()
        
        # Current thread ID for conversation
        self.current_thread_id = None
    
    def _init_database(self):
        """Initialize SQLite database for conversation metadata"""
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                thread_id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT,
                last_updated TEXT,
                message_count INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_conversation(self, title: str = None) -> str:
        """
        Create a new conversation thread
        
        Args:
            title: Optional title for the conversation
            
        Returns:
            thread_id: Unique identifier for the conversation
        """
        from uuid import uuid4
        thread_id = str(uuid4())
        
        if title is None:
            title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversations (thread_id, title, created_at, last_updated)
            VALUES (?, ?, ?, ?)
        """, (thread_id, title, datetime.now().isoformat(), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        self.current_thread_id = thread_id
        return thread_id
    
    def set_current_thread(self, thread_id: str):
        """Set the current conversation thread"""
        self.current_thread_id = thread_id
    
    def get_current_thread(self) -> str:
        """Get current thread ID, create one if none exists"""
        if self.current_thread_id is None:
            self.current_thread_id = self.create_conversation()
        return self.current_thread_id
    
    def _count_tokens(self, messages: List[BaseMessage]) -> int:
        """Count tokens in a list of messages"""
        total_tokens = 0
        for message in messages:
            if hasattr(message, 'content') and message.content:
                tokens = self.encoding.encode(str(message.content))
                total_tokens += len(tokens)
        return total_tokens
    
    def _trim_messages_by_tokens(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Trim messages to fit within token limit while preserving conversation flow
        Always keeps the most recent messages and tries to keep complete exchanges
        """
        if not messages:
            return messages
        
        # Calculate current token count
        current_tokens = self._count_tokens(messages)
        
        if current_tokens <= self.max_token_limit:
            return messages
        
        # Start from the end and keep messages until we exceed token limit
        trimmed_messages = []
        token_count = 0
        
        # Work backwards from most recent messages
        for message in reversed(messages):
            message_tokens = self._count_tokens([message])
            
            if token_count + message_tokens <= self.max_token_limit:
                trimmed_messages.insert(0, message)
                token_count += message_tokens
            else:
                break
        
        # Ensure we have at least the last exchange if possible
        if not trimmed_messages and messages:
            # Take at least the last message even if it exceeds limit
            trimmed_messages = [messages[-1]]
        
        return trimmed_messages
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]):
        """
        Save conversation context to LangGraph memory
        
        Args:
            inputs: Input dictionary (e.g., {"question": "user question"})
            outputs: Output dictionary (e.g., {"answer": "ai response"})
        """
        thread_id = self.get_current_thread()
        
        # Create messages from inputs and outputs
        user_message = HumanMessage(content=inputs.get("question", ""))
        ai_message = AIMessage(content=outputs.get("answer", ""))
        
        # Get existing messages or initialize empty list
        messages = self._thread_messages.get(thread_id, [])
        
        # Add new messages
        messages.extend([user_message, ai_message])
        
        # Trim messages by token limit
        messages = self._trim_messages_by_tokens(messages)
        
        # Save to simple in-memory storage
        self._thread_messages[thread_id] = messages
        
        # Update database metadata
        self._update_conversation_metadata(thread_id, len(messages), self._count_tokens(messages))
    
    def _update_conversation_metadata(self, thread_id: str, message_count: int, token_count: int):
        """Update conversation metadata in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE conversations 
            SET last_updated = ?, message_count = ?, total_tokens = ?
            WHERE thread_id = ?
        """, (datetime.now().isoformat(), message_count, token_count, thread_id))
        
        conn.commit()
        conn.close()
    
    def get_chat_history(self) -> List[BaseMessage]:
        """Get chat history for current thread"""
        thread_id = self.get_current_thread()
        return self._thread_messages.get(thread_id, [])
    
    def get_memory_variables(self) -> Dict[str, Any]:
        """Get memory variables for LLM context (compatibility method)"""
        return {"chat_history": self.get_chat_history()}
    
    def clear(self):
        """Clear current conversation memory"""
        if self.current_thread_id:
            # Clear the thread messages
            self._thread_messages[self.current_thread_id] = []
            
            # Update database
            self._update_conversation_metadata(self.current_thread_id, 0, 0)
    
    def get_token_count(self) -> int:
        """Get current token count in memory"""
        messages = self.get_chat_history()
        return self._count_tokens(messages)
    
    def list_conversations(self) -> List[Dict[str, Any]]:
        """List all conversations with metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT thread_id, title, created_at, last_updated, message_count, total_tokens
            FROM conversations
            ORDER BY last_updated DESC
        """)
        
        conversations = []
        for row in cursor.fetchall():
            conversations.append({
                "thread_id": row[0],
                "title": row[1],
                "created_at": row[2],
                "last_updated": row[3],
                "message_count": row[4],
                "total_tokens": row[5]
            })
        
        conn.close()
        return conversations
    
    def delete_conversation(self, thread_id: str):
        """Delete a conversation and its memory"""
        # Remove from thread messages
        if thread_id in self._thread_messages:
            del self._thread_messages[thread_id]
        
        # Remove from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE thread_id = ?", (thread_id,))
        conn.commit()
        conn.close()
        
        # Reset current thread if it was deleted
        if self.current_thread_id == thread_id:
            self.current_thread_id = None
    
    def get_conversation_summary(self, thread_id: str = None) -> Dict[str, Any]:
        """Get summary of a conversation"""
        if thread_id is None:
            thread_id = self.get_current_thread()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT title, created_at, last_updated, message_count, total_tokens
            FROM conversations WHERE thread_id = ?
        """, (thread_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "thread_id": thread_id,
                "title": row[0],
                "created_at": row[1],
                "last_updated": row[2],
                "message_count": row[3],
                "total_tokens": row[4],
                "current_messages": len(self.get_chat_history()) if thread_id == self.current_thread_id else None
            }
        return {}


def create_langgraph_memory_manager() -> LangGraphMemoryManager:
    """Create a new LangGraph memory manager instance"""
    return LangGraphMemoryManager()


# Backward compatibility wrapper
class ConversationMemory:
    """
    Backward compatibility wrapper for ConversationTokenBufferMemory
    that uses LangGraph memory under the hood
    """
    
    def __init__(self, max_token_limit: int = None):
        self.manager = LangGraphMemoryManager(max_token_limit)
        # For compatibility, mimic the old interface
        self.memory_key = "chat_history"
        self.input_key = "question"
        self.output_key = "answer"
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]):
        """Save context - compatibility method"""
        self.manager.save_context(inputs, outputs)
    
    def get_memory_variables(self) -> Dict[str, Any]:
        """Get memory variables - compatibility method"""
        return self.manager.get_memory_variables()
    
    def clear(self):
        """Clear memory - compatibility method"""
        self.manager.clear()
    
    def get_chat_history(self) -> List[BaseMessage]:
        """Get chat history - compatibility method"""
        return self.manager.get_chat_history()
    
    def get_token_count(self) -> int:
        """Get token count - compatibility method"""
        return self.manager.get_token_count()


def create_memory_manager() -> ConversationMemory:
    """Create backward compatible memory manager"""
    return ConversationMemory()