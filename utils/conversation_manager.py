import streamlit as st
from core.langgraph_memory import create_langgraph_memory_manager, create_memory_manager
from datetime import datetime

def _migrate_old_session_state():
    """Migrate old session state format to new consolidated structure"""
    # Check if we have old format conversations (list-based)
    if "conversations" in st.session_state:
        conversations = st.session_state.conversations
        
        # If any conversation is still a list, migrate to new format
        needs_migration = any(isinstance(conv, list) for conv in conversations.values())
        
        if needs_migration:
            manager = st.session_state.langgraph_manager
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
            
            st.session_state.conversations = new_conversations
            
            # Migrate other old session state keys
            if "conversation_welcome_shown" in st.session_state:
                del st.session_state.conversation_welcome_shown
            if "conversation_memories" in st.session_state:
                del st.session_state.conversation_memories
            if "conversation_threads" in st.session_state:
                del st.session_state.conversation_threads


def initialize_conversations():
    """Initialize simplified conversation state with consolidated structure"""
    if "langgraph_manager" not in st.session_state:
        # Create shared LangGraph manager for all conversations
        st.session_state.langgraph_manager = create_langgraph_memory_manager()
    
    # Migrate old session state format if needed
    _migrate_old_session_state()
    
    if "conversations" not in st.session_state:
        # Simplified conversation structure
        manager = st.session_state.langgraph_manager
        thread_id = manager.create_conversation("Conversation 1")
        
        st.session_state.conversations = {
            "conversation 1": {
                "thread_id": thread_id,
                "title": "Conversation 1",
                "messages": [],
                "welcome_shown": False,
                "memory_manager": create_memory_manager()
            }
        }
        
    if "current_conversation" not in st.session_state:
        st.session_state.current_conversation = "conversation 1"
        
    if "pending_prompt" not in st.session_state:
        # Store prompt from welcome buttons to process
        st.session_state.pending_prompt = None
        
    # Set current thread in LangGraph manager
    current_conv = st.session_state.current_conversation
    if current_conv in st.session_state.conversations:
        # Add safety check for conversation structure
        conversation = st.session_state.conversations[current_conv]
        if isinstance(conversation, dict) and "thread_id" in conversation:
            thread_id = conversation["thread_id"]
            st.session_state.langgraph_manager.set_current_thread(thread_id)

def get_conversation_names():
    """Get list of conversation names"""
    return list(st.session_state.conversations.keys())

def get_current_conversation():
    """Get the current conversation name"""
    return st.session_state.current_conversation

def set_current_conversation(conversation_name):
    """Set the current conversation and update LangGraph thread"""
    if conversation_name not in st.session_state.conversations:
        return  # Invalid conversation name
        
    conversation = st.session_state.conversations[conversation_name]
    
    # Safety check for conversation structure
    if not isinstance(conversation, dict) or "thread_id" not in conversation:
        # Force re-initialization if conversation structure is invalid
        initialize_conversations()
        return
        
    st.session_state.current_conversation = conversation_name
    
    # Update LangGraph manager to use the correct thread
    thread_id = conversation["thread_id"]
    st.session_state.langgraph_manager.set_current_thread(thread_id)

def get_current_messages():
    """Get messages from current conversation"""
    current_conv = st.session_state.current_conversation
    conversation = st.session_state.conversations.get(current_conv, {})
    
    # Safety check for conversation structure
    if not isinstance(conversation, dict) or "messages" not in conversation:
        # Return empty list if conversation structure is invalid
        return []
        
    return conversation["messages"]

def get_current_memory():
    """Get memory manager for current conversation"""
    current_conv = get_current_conversation()
    conversation = st.session_state.conversations.get(current_conv, {})
    
    # Safety check for conversation structure
    if not isinstance(conversation, dict) or "thread_id" not in conversation:
        # Force re-initialization if conversation structure is invalid
        initialize_conversations()
        conversation = st.session_state.conversations.get(current_conv, {})
    
    # Ensure LangGraph manager is using the correct thread
    thread_id = conversation["thread_id"]
    st.session_state.langgraph_manager.set_current_thread(thread_id)
    
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
    conversation_names = get_conversation_names()
    new_name = f"conversation {len(conversation_names) + 1}"
    title = f"Conversation {len(conversation_names) + 1}"
    
    # Create new LangGraph thread
    manager = st.session_state.langgraph_manager
    thread_id = manager.create_conversation(title)
    
    # Create new conversation with consolidated structure
    st.session_state.conversations[new_name] = {
        "thread_id": thread_id,
        "title": title,
        "messages": [],
        "welcome_shown": False,
        "memory_manager": create_memory_manager()
    }
    
    # Set as current conversation
    st.session_state.current_conversation = new_name
    manager.set_current_thread(thread_id)
    
    return new_name

def clear_conversation_memory(conversation_name=None):
    """Clear memory for a specific conversation or current conversation"""
    if conversation_name is None:
        conversation_name = get_current_conversation()
    
    if conversation_name not in st.session_state.conversations:
        return  # Invalid conversation name
    
    conversation = st.session_state.conversations[conversation_name]
    
    # Clear Streamlit conversation messages
    conversation["messages"] = []
    
    # Reset welcome state
    conversation["welcome_shown"] = False
    
    # Clear memory manager
    conversation["memory_manager"].clear()
    
    # Clear LangGraph thread memory
    thread_id = conversation["thread_id"]
    manager = st.session_state.langgraph_manager
    original_thread = manager.current_thread_id
    manager.set_current_thread(thread_id)
    manager.clear()
    # Restore original thread if different
    if original_thread and original_thread != thread_id:
        manager.set_current_thread(original_thread)


def get_conversation_summary(conversation_name=None):
    """Get summary of a conversation using LangGraph memory"""
    if conversation_name is None:
        conversation_name = get_current_conversation()
    
    if conversation_name not in st.session_state.conversations:
        return {}
    
    thread_id = st.session_state.conversations[conversation_name]["thread_id"]
    manager = st.session_state.langgraph_manager
    return manager.get_conversation_summary(thread_id)


def list_all_conversations():
    """List all conversations with their LangGraph summaries"""
    manager = st.session_state.langgraph_manager
    return manager.list_conversations()


def delete_conversation(conversation_name):
    """Delete a conversation completely"""
    if conversation_name == "conversation 1":
        # Don't delete the first conversation, just clear it
        clear_conversation_memory(conversation_name)
        return
    
    if conversation_name not in st.session_state.conversations:
        return  # Invalid conversation name
    
    # Delete LangGraph thread
    thread_id = st.session_state.conversations[conversation_name]["thread_id"]
    manager = st.session_state.langgraph_manager
    manager.delete_conversation(thread_id)
    
    # Remove from Streamlit state
    del st.session_state.conversations[conversation_name]
    
    # Switch to first conversation if current was deleted
    if st.session_state.current_conversation == conversation_name:
        first_conv = list(st.session_state.conversations.keys())[0]
        set_current_conversation(first_conv)


def should_show_welcome_message(conversation_name=None):
    """Check if welcome message should be shown for a conversation"""
    if conversation_name is None:
        conversation_name = get_current_conversation()
    
    if conversation_name not in st.session_state.conversations:
        return False
    
    conversation = st.session_state.conversations[conversation_name]
    # Show welcome if conversation is empty and welcome hasn't been shown yet
    return len(conversation["messages"]) == 0 and not conversation["welcome_shown"]


def mark_welcome_shown(conversation_name=None):
    """Mark welcome message as shown for a conversation"""
    if conversation_name is None:
        conversation_name = get_current_conversation()
    
    if conversation_name in st.session_state.conversations:
        st.session_state.conversations[conversation_name]["welcome_shown"] = True


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
    """Reset all session state - useful for troubleshooting"""
    keys_to_remove = [
        "conversations", "current_conversation", "langgraph_manager",
        "conversation_memories", "conversation_threads", "conversation_welcome_shown",
        "pending_prompt"
    ]
    
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]
    
    # Re-initialize with clean state
    initialize_conversations() 