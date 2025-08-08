"""
Conversation manager service - handles conversation state and operations.
Refactored from utils/conversation_manager.py into a service-oriented architecture.
"""

import streamlit as st
from datetime import datetime
from typing import Optional, Dict, List
import uuid

from services.chat_service.models import Conversation, Message, ConversationSummary
from services.chat_service.memory_repository import get_memory_repository
from infrastructure.monitoring.logging_service import get_logger


class ConversationManager:
    """
    Service for managing conversation state and operations.
    Handles conversation creation, switching, and state management.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.memory_repository = get_memory_repository()
    
    def _get_current_user_id(self) -> Optional[str]:
        """Get current user ID from session state, returns None for guests/unauthenticated"""
        if "user_session" in st.session_state:
            user_session = st.session_state.user_session
            if isinstance(user_session, dict):
                return user_session.get("user_id")
        return None
    
    def _get_user_conversations_key(self, user_id: Optional[str] = None) -> str:
        """Get the session state key for user's conversations"""
        if user_id is None:
            user_id = self._get_current_user_id()
        
        if user_id:
            return f"conversations_{user_id}"
        else:
            return "conversations"  # Fallback for guest/unauthenticated users
    
    def _get_user_langgraph_manager_key(self, user_id: Optional[str] = None) -> str:
        """Get the session state key for user's LangGraph manager"""
        if user_id is None:
            user_id = self._get_current_user_id()
        
        if user_id:
            return f"langgraph_manager_{user_id}"
        else:
            return "langgraph_manager"  # Fallback for guest/unauthenticated users
    
    def initialize_conversations(self):
        """Initialize conversation system for current user"""
        try:
            user_id = self._get_current_user_id()
            conversations_key = self._get_user_conversations_key(user_id)
            manager_key = self._get_user_langgraph_manager_key(user_id)
            current_conversation_key = f"current_conversation_{user_id or 'guest'}"
            
            # Initialize LangGraph memory manager
            if manager_key not in st.session_state:
                st.session_state[manager_key] = self.memory_repository
            
            # Initialize conversations dict
            if conversations_key not in st.session_state:
                st.session_state[conversations_key] = {}
            
            # Initialize current conversation
            if current_conversation_key not in st.session_state:
                st.session_state[current_conversation_key] = "conversation 1"
            
            # Create default conversation if none exist
            conversations = st.session_state[conversations_key]
            if not conversations:
                self.create_new_conversation("conversation 1")
            
            self.logger.info("Conversations initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing conversations: {e}")
            raise
    
    def create_new_conversation(self, conversation_name: str = None) -> str:
        """
        Create a new conversation
        
        Args:
            conversation_name: Name for the conversation
            
        Returns:
            Conversation name/key
        """
        try:
            user_id = self._get_current_user_id()
            conversations_key = self._get_user_conversations_key(user_id)
            manager_key = self._get_user_langgraph_manager_key(user_id)
            
            # Get or create manager
            if manager_key not in st.session_state:
                st.session_state[manager_key] = self.memory_repository
            
            manager = st.session_state[manager_key]
            
            # Generate conversation name if not provided
            if not conversation_name:
                conversations = st.session_state.get(conversations_key, {})
                conversation_name = f"conversation {len(conversations) + 1}"
            
            # Create thread in memory system
            thread_id = manager.create_conversation()
            
            # Initialize conversation data
            conversations = st.session_state.get(conversations_key, {})
            conversations[conversation_name] = {
                "thread_id": thread_id,
                "title": conversation_name.title(),
                "messages": [],
                "welcome_shown": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            st.session_state[conversations_key] = conversations
            
            self.logger.info(f"Created new conversation: {conversation_name}")
            return conversation_name
            
        except Exception as e:
            self.logger.error(f"Error creating conversation: {e}")
            raise
    
    def get_conversation_names(self) -> List[str]:
        """Get list of conversation names for current user"""
        try:
            user_id = self._get_current_user_id()
            conversations_key = self._get_user_conversations_key(user_id)
            
            conversations = st.session_state.get(conversations_key, {})
            return list(conversations.keys())
            
        except Exception as e:
            self.logger.error(f"Error getting conversation names: {e}")
            return []
    
    def get_current_conversation(self) -> str:
        """Get current conversation name"""
        try:
            user_id = self._get_current_user_id()
            current_conversation_key = f"current_conversation_{user_id or 'guest'}"
            
            return st.session_state.get(current_conversation_key, "conversation 1")
            
        except Exception as e:
            self.logger.error(f"Error getting current conversation: {e}")
            return "conversation 1"
    
    def set_current_conversation(self, conversation_name: str):
        """Set current conversation"""
        try:
            user_id = self._get_current_user_id()
            current_conversation_key = f"current_conversation_{user_id or 'guest'}"
            conversations_key = self._get_user_conversations_key(user_id)
            manager_key = self._get_user_langgraph_manager_key(user_id)
            
            # Validate conversation exists
            conversations = st.session_state.get(conversations_key, {})
            if conversation_name not in conversations:
                self.logger.warning(f"Conversation not found: {conversation_name}")
                return
            
            # Set current conversation
            st.session_state[current_conversation_key] = conversation_name
            
            # Update memory manager thread
            manager = st.session_state.get(manager_key)
            if manager and hasattr(manager, 'set_current_thread'):
                thread_id = conversations[conversation_name]["thread_id"]
                manager.set_current_thread(thread_id)
            
            self.logger.info(f"Switched to conversation: {conversation_name}")
            
        except Exception as e:
            self.logger.error(f"Error setting current conversation: {e}")
    
    def get_current_messages(self) -> List[Dict]:
        """Get messages for current conversation"""
        try:
            current_conversation = self.get_current_conversation()
            user_id = self._get_current_user_id()
            conversations_key = self._get_user_conversations_key(user_id)
            
            conversations = st.session_state.get(conversations_key, {})
            if current_conversation not in conversations:
                return []
            
            return conversations[current_conversation].get("messages", [])
            
        except Exception as e:
            self.logger.error(f"Error getting current messages: {e}")
            return []
    
    def add_message(self, role: str, content: str):
        """Add message to current conversation"""
        try:
            current_conversation = self.get_current_conversation()
            user_id = self._get_current_user_id()
            conversations_key = self._get_user_conversations_key(user_id)
            manager_key = self._get_user_langgraph_manager_key(user_id)
            
            # Get conversation data
            conversations = st.session_state.get(conversations_key, {})
            if current_conversation not in conversations:
                self.logger.warning(f"Conversation not found: {current_conversation}")
                return
            
            conversation_data = conversations[current_conversation]
            
            # Add to conversation messages
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            conversation_data["messages"].append(message)
            conversation_data["updated_at"] = datetime.now().isoformat()
            
            # Add to memory repository
            manager = st.session_state.get(manager_key)
            if manager and hasattr(manager, 'add_message'):
                thread_id = conversation_data["thread_id"]
                manager.add_message(thread_id, role, content)
            
            # Update session state
            conversations[current_conversation] = conversation_data
            st.session_state[conversations_key] = conversations
            
            self.logger.debug(f"Added message to conversation {current_conversation}")
            
        except Exception as e:
            self.logger.error(f"Error adding message: {e}")
    
    def get_current_memory(self):
        """Get memory manager for current conversation"""
        try:
            user_id = self._get_current_user_id()
            manager_key = self._get_user_langgraph_manager_key(user_id)
            
            manager = st.session_state.get(manager_key)
            if not manager:
                manager = self.memory_repository
                st.session_state[manager_key] = manager
            
            # Set current thread if needed
            current_conversation = self.get_current_conversation()
            conversations_key = self._get_user_conversations_key(user_id)
            conversations = st.session_state.get(conversations_key, {})
            
            if current_conversation in conversations and hasattr(manager, 'set_current_thread'):
                thread_id = conversations[current_conversation]["thread_id"]
                manager.set_current_thread(thread_id)
            
            return manager
            
        except Exception as e:
            self.logger.error(f"Error getting current memory: {e}")
            return self.memory_repository
    
    def should_show_welcome_message(self) -> bool:
        """Check if welcome message should be shown for current conversation"""
        try:
            current_conversation = self.get_current_conversation()
            user_id = self._get_current_user_id()
            conversations_key = self._get_user_conversations_key(user_id)
            
            conversations = st.session_state.get(conversations_key, {})
            if current_conversation not in conversations:
                return True
            
            conversation_data = conversations[current_conversation]
            messages = conversation_data.get("messages", [])
            welcome_shown = conversation_data.get("welcome_shown", False)
            
            # Show welcome if no messages and not previously shown
            return len(messages) == 0 and not welcome_shown
            
        except Exception as e:
            self.logger.error(f"Error checking welcome message: {e}")
            return True
    
    def mark_welcome_shown(self):
        """Mark welcome message as shown for current conversation"""
        try:
            current_conversation = self.get_current_conversation()
            user_id = self._get_current_user_id()
            conversations_key = self._get_user_conversations_key(user_id)
            
            conversations = st.session_state.get(conversations_key, {})
            if current_conversation in conversations:
                conversations[current_conversation]["welcome_shown"] = True
                st.session_state[conversations_key] = conversations
                
                self.logger.debug(f"Marked welcome as shown for {current_conversation}")
            
        except Exception as e:
            self.logger.error(f"Error marking welcome shown: {e}")
    
    def get_pending_prompt(self) -> Optional[str]:
        """Get pending prompt from session state and clear it"""
        prompt = st.session_state.get("pending_prompt")
        if prompt is not None:
            self.clear_pending_prompt()
        return prompt
    
    def set_pending_prompt(self, prompt: str):
        """Set pending prompt in session state"""
        st.session_state["pending_prompt"] = prompt
    
    def clear_pending_prompt(self):
        """Clear pending prompt from session state"""
        if "pending_prompt" in st.session_state:
            del st.session_state["pending_prompt"]
    
    def process_templated_prompt(self, prompt: str):
        """Process a templated prompt by setting it as pending"""
        self.set_pending_prompt(prompt)
        # Mark welcome as shown since user is interacting
        self.mark_welcome_shown()
    
    def delete_conversation(self, conversation_name: str) -> bool:
        """Delete a conversation"""
        try:
            user_id = self._get_current_user_id()
            conversations_key = self._get_user_conversations_key(user_id)
            manager_key = self._get_user_langgraph_manager_key(user_id)
            current_conversation_key = f"current_conversation_{user_id or 'guest'}"
            
            conversations = st.session_state.get(conversations_key, {})
            
            if conversation_name not in conversations:
                self.logger.warning(f"Conversation not found for deletion: {conversation_name}")
                return False
            
            # Get thread ID before deletion
            thread_id = conversations[conversation_name]["thread_id"]
            
            # Delete from memory repository
            manager = st.session_state.get(manager_key)
            if manager and hasattr(manager, 'delete_conversation'):
                manager.delete_conversation(thread_id)
            
            # Remove from conversations
            del conversations[conversation_name]
            st.session_state[conversations_key] = conversations
            
            # If this was the current conversation, switch to another
            if st.session_state.get(current_conversation_key) == conversation_name:
                remaining_conversations = list(conversations.keys())
                if remaining_conversations:
                    self.set_current_conversation(remaining_conversations[0])
                else:
                    # Create a new conversation if none remain
                    new_conv = self.create_new_conversation()
                    self.set_current_conversation(new_conv)
            
            self.logger.info(f"Deleted conversation: {conversation_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting conversation: {e}")
            return False
    
    def clear_conversation_memory(self, conversation_name: str = None):
        """Clear memory for a conversation"""
        try:
            if conversation_name is None:
                conversation_name = self.get_current_conversation()
            
            user_id = self._get_current_user_id()
            conversations_key = self._get_user_conversations_key(user_id)
            manager_key = self._get_user_langgraph_manager_key(user_id)
            
            conversations = st.session_state.get(conversations_key, {})
            if conversation_name not in conversations:
                return
            
            # Clear messages
            conversations[conversation_name]["messages"] = []
            conversations[conversation_name]["welcome_shown"] = False
            conversations[conversation_name]["updated_at"] = datetime.now().isoformat()
            st.session_state[conversations_key] = conversations
            
            # Clear from memory repository
            manager = st.session_state.get(manager_key)
            if manager and hasattr(manager, 'clear_history'):
                thread_id = conversations[conversation_name]["thread_id"]
                manager.clear_history(thread_id)
            
            self.logger.info(f"Cleared memory for conversation: {conversation_name}")
            
        except Exception as e:
            self.logger.error(f"Error clearing conversation memory: {e}")
    
    def update_conversation_title(self, conversation_name: str, new_title: str):
        """Update conversation title"""
        try:
            user_id = self._get_current_user_id()
            conversations_key = self._get_user_conversations_key(user_id)
            
            conversations = st.session_state.get(conversations_key, {})
            if conversation_name in conversations:
                conversations[conversation_name]["title"] = new_title
                conversations[conversation_name]["updated_at"] = datetime.now().isoformat()
                st.session_state[conversations_key] = conversations
                
                self.logger.info(f"Updated title for {conversation_name}: {new_title}")
            
        except Exception as e:
            self.logger.error(f"Error updating conversation title: {e}")
    
    def reset_session_state(self):
        """Reset session state (clear all conversations)"""
        try:
            user_id = self._get_current_user_id()
            conversations_key = self._get_user_conversations_key(user_id)
            manager_key = self._get_user_langgraph_manager_key(user_id)
            current_conversation_key = f"current_conversation_{user_id or 'guest'}"
            
            # Clear session state keys
            keys_to_clear = [conversations_key, manager_key, current_conversation_key, "pending_prompt"]
            
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            self.logger.info("Reset session state")
            
        except Exception as e:
            self.logger.error(f"Error resetting session state: {e}")


# Global conversation manager instance
_conversation_manager: Optional[ConversationManager] = None


def get_conversation_manager() -> ConversationManager:
    """Get the global conversation manager instance"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager


# Legacy compatibility functions for existing imports
def initialize_conversations():
    """Initialize conversations (legacy compatibility)"""
    manager = get_conversation_manager()
    manager.initialize_conversations()


def get_current_conversation():
    """Get current conversation (legacy compatibility)"""
    manager = get_conversation_manager()
    return manager.get_current_conversation()


def set_current_conversation(conversation_name: str):
    """Set current conversation (legacy compatibility)"""
    manager = get_conversation_manager()
    manager.set_current_conversation(conversation_name)


def get_conversation_names():
    """Get conversation names (legacy compatibility)"""
    manager = get_conversation_manager()
    return manager.get_conversation_names()


def create_new_conversation(conversation_name: str = None):
    """Create new conversation (legacy compatibility)"""
    manager = get_conversation_manager()
    return manager.create_new_conversation(conversation_name)


def get_current_messages():
    """Get current messages (legacy compatibility)"""
    manager = get_conversation_manager()
    return manager.get_current_messages()


def add_message(role: str, content: str):
    """Add message (legacy compatibility)"""
    manager = get_conversation_manager()
    manager.add_message(role, content)


def get_current_memory():
    """Get current memory (legacy compatibility)"""
    manager = get_conversation_manager()
    return manager.get_current_memory()


def should_show_welcome_message():
    """Should show welcome message (legacy compatibility)"""
    manager = get_conversation_manager()
    return manager.should_show_welcome_message()


def get_pending_prompt():
    """Get pending prompt and clear it (legacy compatibility)"""
    manager = get_conversation_manager()
    return manager.get_pending_prompt()


def set_pending_prompt(prompt: str):
    """Set pending prompt (legacy compatibility)"""
    manager = get_conversation_manager()
    manager.set_pending_prompt(prompt)


def process_templated_prompt(prompt: str):
    """Process templated prompt (legacy compatibility)"""
    manager = get_conversation_manager()
    manager.process_templated_prompt(prompt)


def clear_conversation_memory(conversation_name: str = None):
    """Clear conversation memory (legacy compatibility)"""
    manager = get_conversation_manager()
    manager.clear_conversation_memory(conversation_name)


def reset_session_state():
    """Reset session state (legacy compatibility)"""
    manager = get_conversation_manager()
    manager.reset_session_state()


def update_conversation_title(conversation_name: str, new_title: str):
    """Update conversation title (legacy compatibility)"""
    manager = get_conversation_manager()
    manager.update_conversation_title(conversation_name, new_title)