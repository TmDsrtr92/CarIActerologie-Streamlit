"""
Memory repository - handles conversation memory and persistence.
Refactored from core/langgraph_memory.py into a service-oriented architecture.
"""

from typing import Dict, Any, List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState
from langchain_openai import ChatOpenAI
import tiktoken
import sqlite3
import json
import os
import uuid
from datetime import datetime

from services.chat_service.models import Message, Conversation, ConversationSummary
from infrastructure.config.settings import get_openai_api_key, get_config
from infrastructure.monitoring.logging_service import get_logger


class MemoryRepository:
    """
    Repository for conversation memory management and persistence.
    Handles LangGraph memory operations and database persistence.
    """
    
    def __init__(self, max_token_limit: int = None, db_path: str = "infrastructure/database/conversations/conversations.db"):
        """
        Initialize memory repository
        
        Args:
            max_token_limit: Maximum tokens to keep in memory
            db_path: Path to SQLite database for persistence
        """
        config = get_config()
        self.logger = get_logger(__name__)
        self.max_token_limit = max_token_limit or config.memory.max_token_limit
        self.model_name = config.memory.model_name
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
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create conversations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    thread_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    token_count INTEGER DEFAULT 0
                )
            ''')
            
            # Create messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    token_count INTEGER DEFAULT 0,
                    FOREIGN KEY (thread_id) REFERENCES conversations (thread_id)
                )
            ''')
            
            # Run database migrations
            self._run_migrations(cursor)
            
            # Create index for better performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages (thread_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp)
            ''')
            
            conn.commit()
            conn.close()
            
            self.logger.info("Memory database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing memory database: {e}")
            raise
    
    def _run_migrations(self, cursor):
        """Run database schema migrations"""
        try:
            # Check if conversations table exists and what columns it has
            cursor.execute("PRAGMA table_info(conversations)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Migration 1: Add updated_at column if missing
            if 'updated_at' not in columns and 'thread_id' in columns:
                self.logger.info("Adding updated_at column to conversations table")
                cursor.execute("ALTER TABLE conversations ADD COLUMN updated_at TEXT")
                # Set default value for existing records
                now = datetime.now().isoformat()
                cursor.execute("UPDATE conversations SET updated_at = ? WHERE updated_at IS NULL", (now,))
                self.logger.info("Migration 1 completed: updated_at column added")
            
            # Migration 2: Add message_count column if missing
            if 'message_count' not in columns and 'thread_id' in columns:
                self.logger.info("Adding message_count column to conversations table")
                cursor.execute("ALTER TABLE conversations ADD COLUMN message_count INTEGER DEFAULT 0")
                # Update counts for existing conversations
                cursor.execute('''
                    UPDATE conversations 
                    SET message_count = (
                        SELECT COUNT(*) FROM messages 
                        WHERE messages.thread_id = conversations.thread_id
                    )
                    WHERE message_count IS NULL
                ''')
                self.logger.info("Migration 2 completed: message_count column added")
            
            # Migration 3: Add token_count column if missing
            if 'token_count' not in columns and 'thread_id' in columns:
                self.logger.info("Adding token_count column to conversations table")
                cursor.execute("ALTER TABLE conversations ADD COLUMN token_count INTEGER DEFAULT 0")
                self.logger.info("Migration 3 completed: token_count column added")
                
        except Exception as e:
            self.logger.error(f"Error during database migration: {e}")
            # Don't raise - continue with what we have
    
    def create_conversation(self, title: str = None) -> str:
        """
        Create a new conversation thread
        
        Args:
            title: Optional conversation title
            
        Returns:
            Thread ID of the created conversation
        """
        try:
            thread_id = str(uuid.uuid4())
            
            if not title:
                title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Initialize empty message list for this thread
            self._thread_messages[thread_id] = []
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO conversations (thread_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (thread_id, title, now, now))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Created new conversation: {thread_id}")
            return thread_id
            
        except Exception as e:
            self.logger.error(f"Error creating conversation: {e}")
            raise
    
    def add_message(self, thread_id: str, role: str, content: str) -> None:
        """
        Add a message to the conversation
        
        Args:
            thread_id: Thread identifier
            role: Message role (user, assistant, system)
            content: Message content
        """
        try:
            # Create message
            if role == "user":
                message = HumanMessage(content=content)
            elif role == "assistant":
                message = AIMessage(content=content)
            else:
                # For system messages, use AIMessage with system prefix
                message = AIMessage(content=content)
            
            # Initialize thread if not exists
            if thread_id not in self._thread_messages:
                self._thread_messages[thread_id] = []
            
            # Add to in-memory storage
            self._thread_messages[thread_id].append(message)
            
            # Calculate token count for this message
            token_count = len(self.encoding.encode(content))
            
            # Store in database
            self._save_message_to_db(thread_id, role, content, token_count)
            
            # Trim messages if over token limit
            self._trim_messages_if_needed(thread_id)
            
            self.logger.debug(f"Added message to conversation {thread_id}")
            
        except Exception as e:
            self.logger.error(f"Error adding message: {e}")
            raise
    
    def get_messages(self, thread_id: str) -> List[BaseMessage]:
        """
        Get all messages for a thread
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            List of BaseMessage objects
        """
        if thread_id not in self._thread_messages:
            # Try to load from database
            self._load_messages_from_db(thread_id)
        
        return self._thread_messages.get(thread_id, [])
    
    def get_chat_history(self, thread_id: str = None) -> List[BaseMessage]:
        """
        Get chat history for current or specified thread
        
        Args:
            thread_id: Thread identifier (uses current if None)
            
        Returns:
            List of BaseMessage objects
        """
        if thread_id is None:
            thread_id = self.current_thread_id
        
        if thread_id is None:
            return []
        
        return self.get_messages(thread_id)
    
    def get_token_count(self, thread_id: str = None) -> int:
        """
        Get token count for current or specified thread
        
        Args:
            thread_id: Thread identifier (uses current if None)
            
        Returns:
            Total token count
        """
        if thread_id is None:
            thread_id = self.current_thread_id
        
        if thread_id is None:
            return 0
        
        messages = self.get_messages(thread_id)
        total_tokens = 0
        
        for message in messages:
            total_tokens += len(self.encoding.encode(message.content))
        
        return total_tokens
    
    def clear_history(self, thread_id: str = None) -> None:
        """
        Clear chat history for current or specified thread
        
        Args:
            thread_id: Thread identifier (uses current if None)
        """
        if thread_id is None:
            thread_id = self.current_thread_id
        
        if thread_id is None:
            return
        
        try:
            # Clear from memory
            if thread_id in self._thread_messages:
                del self._thread_messages[thread_id]
            
            # Clear from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM messages WHERE thread_id = ?', (thread_id,))
            cursor.execute('''
                UPDATE conversations 
                SET message_count = 0, token_count = 0, updated_at = ?
                WHERE thread_id = ?
            ''', (datetime.now().isoformat(), thread_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Cleared history for conversation {thread_id}")
            
        except Exception as e:
            self.logger.error(f"Error clearing history: {e}")
            raise
    
    def set_current_thread(self, thread_id: str) -> None:
        """
        Set the current active thread
        
        Args:
            thread_id: Thread identifier
        """
        self.current_thread_id = thread_id
    
    def list_conversations(self) -> List[ConversationSummary]:
        """
        List all conversations
        
        Returns:
            List of conversation summaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT thread_id, title, created_at, updated_at, message_count, token_count
                FROM conversations
                ORDER BY updated_at DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            summaries = []
            for row in rows:
                thread_id, title, created_at, updated_at, message_count, token_count = row
                
                # Get preview text from latest message
                preview_text = self._get_conversation_preview(thread_id)
                
                summaries.append(ConversationSummary(
                    conversation_id=thread_id,
                    title=title,
                    message_count=message_count or 0,
                    last_activity=datetime.fromisoformat(updated_at),
                    created_at=datetime.fromisoformat(created_at),
                    preview_text=preview_text
                ))
            
            return summaries
            
        except Exception as e:
            self.logger.error(f"Error listing conversations: {e}")
            return []
    
    def delete_conversation(self, thread_id: str) -> bool:
        """
        Delete a conversation and all its messages
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            True if successful
        """
        try:
            # Clear from memory
            if thread_id in self._thread_messages:
                del self._thread_messages[thread_id]
            
            # Delete from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM messages WHERE thread_id = ?', (thread_id,))
            cursor.execute('DELETE FROM conversations WHERE thread_id = ?', (thread_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Deleted conversation {thread_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting conversation: {e}")
            return False
    
    def _save_message_to_db(self, thread_id: str, role: str, content: str, token_count: int):
        """Save message to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            message_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO messages (id, thread_id, role, content, timestamp, token_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (message_id, thread_id, role, content, now, token_count))
            
            # Update conversation metadata
            cursor.execute('''
                UPDATE conversations 
                SET updated_at = ?, 
                    message_count = (SELECT COUNT(*) FROM messages WHERE thread_id = ?),
                    token_count = (SELECT COALESCE(SUM(token_count), 0) FROM messages WHERE thread_id = ?)
                WHERE thread_id = ?
            ''', (now, thread_id, thread_id, thread_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error saving message to database: {e}")
    
    def _load_messages_from_db(self, thread_id: str):
        """Load messages from database into memory"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT role, content FROM messages 
                WHERE thread_id = ? 
                ORDER BY timestamp ASC
            ''', (thread_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            messages = []
            for role, content in rows:
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
                else:
                    messages.append(AIMessage(content=content))
            
            self._thread_messages[thread_id] = messages
            
        except Exception as e:
            self.logger.error(f"Error loading messages from database: {e}")
    
    def _trim_messages_if_needed(self, thread_id: str):
        """Trim messages if over token limit"""
        try:
            messages = self._thread_messages.get(thread_id, [])
            if not messages:
                return
            
            # Calculate current token count
            current_tokens = sum(len(self.encoding.encode(msg.content)) for msg in messages)
            
            # If over limit, remove oldest messages until under limit
            while current_tokens > self.max_token_limit and len(messages) > 1:
                removed_message = messages.pop(0)
                current_tokens -= len(self.encoding.encode(removed_message.content))
                
                # Remove from database too
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM messages 
                    WHERE thread_id = ? 
                    AND id = (
                        SELECT id FROM messages 
                        WHERE thread_id = ? 
                        ORDER BY timestamp ASC 
                        LIMIT 1
                    )
                ''', (thread_id, thread_id))
                conn.commit()
                conn.close()
            
            self.logger.debug(f"Trimmed messages for {thread_id}, now {current_tokens} tokens")
            
        except Exception as e:
            self.logger.error(f"Error trimming messages: {e}")
    
    def _get_conversation_preview(self, thread_id: str) -> Optional[str]:
        """Get preview text for conversation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT content FROM messages 
                WHERE thread_id = ? AND role = 'user'
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (thread_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                content = row[0]
                # Truncate to reasonable preview length
                return content[:100] + "..." if len(content) > 100 else content
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting conversation preview: {e}")
            return None


# Legacy compatibility functions
def create_memory_manager():
    """Create a memory manager (legacy compatibility)"""
    return MemoryRepository()


def create_langgraph_memory_manager():
    """Create a LangGraph memory manager (legacy compatibility)"""
    return MemoryRepository()


# Global memory repository instance
_memory_repository: Optional[MemoryRepository] = None


def get_memory_repository() -> MemoryRepository:
    """Get the global memory repository instance"""
    global _memory_repository
    if _memory_repository is None:
        _memory_repository = MemoryRepository()
    return _memory_repository