import streamlit as st
from core.langgraph_memory import create_langgraph_memory_manager, create_memory_manager
from datetime import datetime
from typing import Optional

def _get_current_user_id() -> Optional[str]:
    """Get current user ID from session state, returns None for guests/unauthenticated"""
    if "user_session" in st.session_state:
        user_session = st.session_state.user_session
        if isinstance(user_session, dict):
            return user_session.get("user_id")
    return None

def _get_user_conversations_key(user_id: Optional[str] = None) -> str:
    """Get the session state key for user's conversations"""
    if user_id is None:
        user_id = _get_current_user_id()
    
    if user_id:
        return f"conversations_{user_id}"
    else:
        return "conversations"  # Fallback for guest/unauthenticated users

def _get_user_langgraph_manager_key(user_id: Optional[str] = None) -> str:
    """Get the session state key for user's LangGraph manager"""
    if user_id is None:
        user_id = _get_current_user_id()
    
    if user_id:
        return f"langgraph_manager_{user_id}"
    else:
        return "langgraph_manager"  # Fallback for guest/unauthenticated users

def _migrate_old_session_state():
    """Migrate old session state format to new consolidated structure"""
    # Get user-specific keys
    conversations_key = _get_user_conversations_key()
    manager_key = _get_user_langgraph_manager_key()
    
    # Check if we have old format conversations (list-based)
    if conversations_key in st.session_state:
        conversations = st.session_state[conversations_key]
        
        # If any conversation is still a list, migrate to new format
        needs_migration = any(isinstance(conv, list) for conv in conversations.values())
        
        if needs_migration:
            manager = st.session_state[manager_key]
            new_conversations = {}
            
            for conv_name, conv_data in conversations.items():
                if isinstance(conv_data, list):
                    # Old format: conversation was a list of messages
                    thread_id = manager.create_conversation(conv_name.title())
                    new_conversations[conv_name] = {
                        "thread_id": thread_id,
                        "title": conv_name.title(),
                        "messages": conv_data,  # Keep existing messages
                        "welcome_shown": len(conv_data) > 0,  # If has messages, welcome was shown
                        "memory_manager": create_memory_manager()
                    }
                else:
                    # Already new format
                    new_conversations[conv_name] = conv_data
            
            st.session_state[conversations_key] = new_conversations
            
            # Migrate other old session state keys (user-specific)
            user_id = _get_current_user_id()
            old_keys = ["conversation_welcome_shown", "conversation_memories", "conversation_threads"]
            for old_key in old_keys:
                if user_id:
                    user_specific_key = f"{old_key}_{user_id}"
                    if user_specific_key in st.session_state:
                        del st.session_state[user_specific_key]
                if old_key in st.session_state:
                    del st.session_state[old_key]


def initialize_conversations():
    """Initialize simplified conversation state with consolidated structure (user-isolated)"""
    # Get user-specific keys
    conversations_key = _get_user_conversations_key()
    manager_key = _get_user_langgraph_manager_key()
    current_conversation_key = f"current_conversation_{_get_current_user_id() or 'guest'}"
    
    if manager_key not in st.session_state:
        # Create user-specific LangGraph manager
        st.session_state[manager_key] = create_langgraph_memory_manager()
    
    # Migrate old session state format if needed
    _migrate_old_session_state()
    
    if conversations_key not in st.session_state:
        # Simplified conversation structure
        manager = st.session_state[manager_key]
        thread_id = manager.create_conversation("Conversation 1")
        
        st.session_state[conversations_key] = {
            "conversation 1": {
                "thread_id": thread_id,
                "title": "Conversation 1",
                "messages": [],
                "welcome_shown": False,
                "memory_manager": create_memory_manager()
            }
        }
        
    if current_conversation_key not in st.session_state:
        st.session_state[current_conversation_key] = "conversation 1"
        
    if "pending_prompt" not in st.session_state:
        # Store prompt from welcome buttons to process (shared across users for simplicity)
        st.session_state.pending_prompt = None
        
    # Set current thread in LangGraph manager
    current_conv = st.session_state[current_conversation_key]
    if current_conv in st.session_state[conversations_key]:
        # Add safety check for conversation structure
        conversation = st.session_state[conversations_key][current_conv]
        if isinstance(conversation, dict) and "thread_id" in conversation:
            thread_id = conversation["thread_id"]
            st.session_state[manager_key].set_current_thread(thread_id)

def get_conversation_names():
    """Get list of conversation names"""
    conversations_key = _get_user_conversations_key()
    return list(st.session_state.get(conversations_key, {}).keys())

def get_current_conversation():
    """Get the current conversation name"""
    current_conversation_key = f"current_conversation_{_get_current_user_id() or 'guest'}"
    return st.session_state.get(current_conversation_key, "conversation 1")

def set_current_conversation(conversation_name):
    """Set the current conversation and update LangGraph thread"""
    conversations_key = _get_user_conversations_key()
    manager_key = _get_user_langgraph_manager_key()
    current_conversation_key = f"current_conversation_{_get_current_user_id() or 'guest'}"
    
    if conversation_name not in st.session_state.get(conversations_key, {}):
        return  # Invalid conversation name
        
    conversation = st.session_state[conversations_key][conversation_name]
    
    # Safety check for conversation structure
    if not isinstance(conversation, dict) or "thread_id" not in conversation:
        # Force re-initialization if conversation structure is invalid
        initialize_conversations()
        return
        
    st.session_state[current_conversation_key] = conversation_name
    
    # Update LangGraph manager to use the correct thread
    thread_id = conversation["thread_id"]
    st.session_state[manager_key].set_current_thread(thread_id)

def get_current_messages():
    """Get messages from current conversation"""
    conversations_key = _get_user_conversations_key()
    current_conv = get_current_conversation()
    conversation = st.session_state.get(conversations_key, {}).get(current_conv, {})
    
    # Safety check for conversation structure
    if not isinstance(conversation, dict) or "messages" not in conversation:
        # Return empty list if conversation structure is invalid
        return []
        
    return conversation["messages"]

def get_current_memory():
    """Get memory manager for current conversation"""
    conversations_key = _get_user_conversations_key()
    manager_key = _get_user_langgraph_manager_key()
    current_conv = get_current_conversation()
    conversation = st.session_state.get(conversations_key, {}).get(current_conv, {})
    
    # Safety check for conversation structure
    if not isinstance(conversation, dict) or "thread_id" not in conversation:
        # Force re-initialization if conversation structure is invalid
        initialize_conversations()
        conversation = st.session_state.get(conversations_key, {}).get(current_conv, {})
    
    # Ensure LangGraph manager is using the correct thread
    thread_id = conversation["thread_id"]
    st.session_state[manager_key].set_current_thread(thread_id)
    
    # Update the memory manager to use the correct LangGraph thread
    memory_manager = conversation["memory_manager"]
    if hasattr(memory_manager, 'manager'):
        memory_manager.manager.set_current_thread(thread_id)
    
    return memory_manager

def add_message(role, content):
    """Add a message to the current conversation"""
    messages = get_current_messages()
    messages.append({"role": role, "content": content})
    
    # Note: Memory is automatically managed by the LangGraph QA chain
    # No need to manually add to memory here

def create_new_conversation():
    """Create a new conversation with its own LangGraph thread and memory"""
    conversations_key = _get_user_conversations_key()
    manager_key = _get_user_langgraph_manager_key()
    current_conversation_key = f"current_conversation_{_get_current_user_id() or 'guest'}"
    
    conversation_names = get_conversation_names()
    new_name = f"conversation {len(conversation_names) + 1}"
    title = f"Conversation {len(conversation_names) + 1}"
    
    # Create new LangGraph thread
    manager = st.session_state[manager_key]
    thread_id = manager.create_conversation(title)
    
    # Create new conversation with consolidated structure
    if conversations_key not in st.session_state:
        st.session_state[conversations_key] = {}
    
    st.session_state[conversations_key][new_name] = {
        "thread_id": thread_id,
        "title": title,
        "messages": [],
        "welcome_shown": False,
        "memory_manager": create_memory_manager()
    }
    
    # Set as current conversation
    st.session_state[current_conversation_key] = new_name
    manager.set_current_thread(thread_id)
    
    return new_name

def clear_conversation_memory(conversation_name=None):
    """Clear memory for a specific conversation or current conversation"""
    conversations_key = _get_user_conversations_key()
    manager_key = _get_user_langgraph_manager_key()
    
    if conversation_name is None:
        conversation_name = get_current_conversation()
    
    if conversation_name not in st.session_state.get(conversations_key, {}):
        return  # Invalid conversation name
    
    conversation = st.session_state[conversations_key][conversation_name]
    
    # Clear Streamlit conversation messages
    conversation["messages"] = []
    
    # Reset welcome state
    conversation["welcome_shown"] = False
    
    # Clear memory manager
    conversation["memory_manager"].clear()
    
    # Clear LangGraph thread memory
    thread_id = conversation["thread_id"]
    manager = st.session_state[manager_key]
    original_thread = manager.current_thread_id
    manager.set_current_thread(thread_id)
    manager.clear()
    # Restore original thread if different
    if original_thread and original_thread != thread_id:
        manager.set_current_thread(original_thread)


def get_conversation_summary(conversation_name=None):
    """Get summary of a conversation using LangGraph memory"""
    conversations_key = _get_user_conversations_key()
    manager_key = _get_user_langgraph_manager_key()
    
    if conversation_name is None:
        conversation_name = get_current_conversation()
    
    if conversation_name not in st.session_state.get(conversations_key, {}):
        return {}
    
    thread_id = st.session_state[conversations_key][conversation_name]["thread_id"]
    manager = st.session_state[manager_key]
    return manager.get_conversation_summary(thread_id)


def list_all_conversations():
    """List all conversations with their LangGraph summaries"""
    manager_key = _get_user_langgraph_manager_key()
    manager = st.session_state.get(manager_key)
    if manager:
        return manager.list_conversations()
    return []


def delete_conversation(conversation_name):
    """Delete a conversation completely"""
    conversations_key = _get_user_conversations_key()
    manager_key = _get_user_langgraph_manager_key()
    current_conversation_key = f"current_conversation_{_get_current_user_id() or 'guest'}"
    
    if conversation_name == "conversation 1":
        # Don't delete the first conversation, just clear it
        clear_conversation_memory(conversation_name)
        return
    
    if conversation_name not in st.session_state.get(conversations_key, {}):
        return  # Invalid conversation name
    
    # Delete LangGraph thread
    thread_id = st.session_state[conversations_key][conversation_name]["thread_id"]
    manager = st.session_state[manager_key]
    manager.delete_conversation(thread_id)
    
    # Remove from Streamlit state
    del st.session_state[conversations_key][conversation_name]
    
    # Switch to first conversation if current was deleted
    if st.session_state.get(current_conversation_key) == conversation_name:
        remaining_conversations = st.session_state.get(conversations_key, {})
        if remaining_conversations:
            first_conv = list(remaining_conversations.keys())[0]
            set_current_conversation(first_conv)


def should_show_welcome_message(conversation_name=None):
    """Check if welcome message should be shown for a conversation"""
    conversations_key = _get_user_conversations_key()
    
    if conversation_name is None:
        conversation_name = get_current_conversation()
    
    if conversation_name not in st.session_state.get(conversations_key, {}):
        return False
    
    conversation = st.session_state[conversations_key][conversation_name]
    # Show welcome if conversation is empty and welcome hasn't been shown yet
    return len(conversation["messages"]) == 0 and not conversation["welcome_shown"]


def mark_welcome_shown(conversation_name=None):
    """Mark welcome message as shown for a conversation"""
    conversations_key = _get_user_conversations_key()
    
    if conversation_name is None:
        conversation_name = get_current_conversation()
    
    if conversation_name in st.session_state.get(conversations_key, {}):
        st.session_state[conversations_key][conversation_name]["welcome_shown"] = True


def set_pending_prompt(prompt_text):
    """Set a prompt to be processed as if user typed it"""
    st.session_state.pending_prompt = prompt_text


def get_pending_prompt():
    """Get and clear any pending prompt"""
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None
    return prompt


def process_templated_prompt(prompt_text):
    """Process a templated prompt as if user submitted it"""
    # Mark welcome as shown for current conversation
    mark_welcome_shown()
    
    # Set the prompt to be processed
    set_pending_prompt(prompt_text)
    
    # Trigger processing
    st.rerun()


def reset_session_state():
    """Reset all session state - useful for troubleshooting (user-specific)"""
    user_id = _get_current_user_id()
    
    # User-specific keys to remove
    user_specific_keys = []
    if user_id:
        user_specific_keys = [
            f"conversations_{user_id}",
            f"current_conversation_{user_id}",
            f"langgraph_manager_{user_id}"
        ]
    
    # Global fallback keys (for guests/unauthenticated)
    global_keys = [
        "conversations", "current_conversation", "langgraph_manager",
        "conversation_memories", "conversation_threads", "conversation_welcome_shown",
        "pending_prompt"
    ]
    
    all_keys = user_specific_keys + global_keys
    
    for key in all_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Re-initialize with clean state
    initialize_conversations() 