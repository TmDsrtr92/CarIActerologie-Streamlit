"""
Chat interface service - handles chat UI components and interactions.
Refactored from utils/streamlit_helpers.py into a service-oriented architecture.
"""

import streamlit as st
import time
from typing import List, Dict, Optional
from langfuse.langchain import CallbackHandler

from infrastructure.config.settings import get_config
from infrastructure.external.langfuse_client import get_langfuse_client
from services.ui_service.callback_handlers import StreamlitCallbackHandler
from services.chat_service.conversation_manager import get_conversation_manager
from infrastructure.monitoring.logging_service import get_logger


class ChatInterface:
    """
    Service for chat interface components and interactions.
    Handles conversation sidebar, message rendering, and streaming.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.conversation_manager = get_conversation_manager()
        self.langfuse_client = get_langfuse_client()
    
    def get_langfuse_handler(self) -> Optional[CallbackHandler]:
        """Get Langfuse callback handler if available"""
        return self.langfuse_client.get_callback_handler()
    
    def create_stream_handler(self, placeholder):
        """Create a streaming callback handler for Streamlit"""
        return StreamlitCallbackHandler(
            placeholder, 
            update_every=self.config.streaming.update_every, 
            delay=self.config.streaming.delay
        )
    
    def render_conversation_sidebar(self):
        """Render the conversation sidebar"""
        config = self.config
        
        conversation_names = self.conversation_manager.get_conversation_names()
        current_conversation = self.conversation_manager.get_current_conversation()
        
        # Get conversations data for title display
        conversations_key = self.conversation_manager._get_user_conversations_key()
        
        with st.sidebar:
            # Enhanced sidebar header
            st.markdown("## 💬 Conversations")
            
            # Add conversation search
            search_query = st.text_input("🔍 Search conversations", placeholder="Search by title or content...")
            
            # Filter conversations based on search
            if search_query:
                filtered_conversations = self._filter_conversations(conversation_names, search_query)
                display_conversations = filtered_conversations
                st.caption(f"🔍 {len(filtered_conversations)} of {len(conversation_names)} conversations")
            else:
                display_conversations = conversation_names
                st.caption(f"📊 {len(conversation_names)} conversation{'s' if len(conversation_names) != 1 else ''}")
            
            # Add filter options
            with st.expander("🎯 Filters", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    show_recent = st.checkbox("Recent only", value=False, help="Show only recent conversations")
                with col2:
                    sort_by = st.selectbox("Sort by", ["Date", "Name"], index=0)
            
            # Apply filters
            if show_recent:
                # Show only last 10 conversations
                display_conversations = display_conversations[:10]
            
            if sort_by == "Name":
                display_conversations = sorted(display_conversations)
            
            # Conversation list
            st.markdown("### Select Conversation")
            
            # Current conversation indicator
            for conv_name in display_conversations:
                if conv_name == current_conversation:
                    if st.button(f"✅ {conv_name}", key=f"current_{conv_name}", use_container_width=True, 
                               help="Currently active conversation", type="primary"):
                        pass  # Already current, no action needed
                else:
                    if st.button(f"💬 {conv_name}", key=f"select_{conv_name}", use_container_width=True):
                        self.conversation_manager.set_current_conversation(conv_name)
                        st.rerun()
            
            # New conversation button
            st.divider()
            if st.button("➕ New Conversation", use_container_width=True, type="secondary"):
                new_conv = self.conversation_manager.create_new_conversation()
                self.conversation_manager.set_current_conversation(new_conv)
                st.rerun()
            
            # Collection selector
            st.markdown("### 🗂️ Collection")
            
            # Get current collection from session state or use default
            if "selected_collection" not in st.session_state:
                st.session_state.selected_collection = config.vectorstore.default_collection_key
            
            # Collection selector
            collection_options = list(config.vectorstore.collections.keys())
            
            # Handle legacy collection names (migration from old format)
            legacy_mapping = {
                "Sub-chapters (Semantic)": "subchapters",
                "Original (Character-based)": "original"
            }
            
            # Check if current selection is a legacy format and migrate it
            if st.session_state.selected_collection in legacy_mapping:
                st.session_state.selected_collection = legacy_mapping[st.session_state.selected_collection]
            
            # Ensure the selected collection exists in current options
            if st.session_state.selected_collection not in collection_options:
                st.session_state.selected_collection = config.vectorstore.default_collection_key
            
            current_index = collection_options.index(st.session_state.selected_collection)
            
            # Create user-friendly display names
            def format_collection_name(key):
                collection = config.vectorstore.collections[key]
                if key == "subchapters":
                    return "📚 Sub-chapters (Semantic)"
                elif key == "original":
                    return "📄 Original (Character-based)"
                else:
                    return f"📚 {key.title()}"
            
            selected_collection = st.selectbox(
                "Select knowledge base:",
                collection_options,
                index=current_index,
                format_func=format_collection_name,
                help="Choose which collection of documents to search"
            )
            
            if selected_collection != st.session_state.selected_collection:
                st.session_state.selected_collection = selected_collection
                st.rerun()
            
            # Display collection info
            collection_info = config.vectorstore.collections[selected_collection]
            st.write(f"**Description:** {collection_info.description}")
            st.write(f"**Type:** {collection_info.chunk_type}")
            
            # Collection status indicator
            if collection_info.chunk_type == 'semantic':
                st.success("✅ Chunking sémantique actif")
            else:
                st.info("ℹ️ Chunking par caractères actif")
            
            # Memory information section
            st.markdown("### 🧠 Memory Status")
            
            current_memory = self.conversation_manager.get_current_memory()
            chat_history = current_memory.get_chat_history()
            token_count = current_memory.get_token_count()
            max_tokens = config.memory.max_token_limit
            
            # Display memory statistics
            st.write(f"**Messages:** {len(chat_history)}")
            st.write(f"**Tokens:** {token_count}/{max_tokens}")
            
            # Memory usage progress bar
            memory_percentage = min(token_count / max_tokens * 100, 100)
            st.progress(memory_percentage / 100)
            
            if memory_percentage > 80:
                st.warning("⚠️ Memory usage high - older messages may be trimmed")
            elif memory_percentage > 95:
                st.error("🚨 Memory nearly full - performance may be affected")
            
            # Conversation management
            st.markdown("### ⚙️ Actions")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear", help="Clear current conversation", use_container_width=True):
                    self.conversation_manager.clear_conversation_memory()
                    st.success("🗑️ Conversation cleared!")
                    st.rerun()
            
            with col2:
                if st.button("📝 Rename", help="Rename current conversation", use_container_width=True):
                    st.session_state.show_rename_dialog = True
            
            # Rename dialog
            if st.session_state.get("show_rename_dialog", False):
                with st.form("rename_conversation"):
                    new_title = st.text_input("New conversation title:", value=current_conversation)
                    col_submit, col_cancel = st.columns(2)
                    
                    with col_submit:
                        if st.form_submit_button("Save", use_container_width=True):
                            if new_title.strip():
                                self.conversation_manager.update_conversation_title(current_conversation, new_title.strip())
                                st.session_state.show_rename_dialog = False
                                st.success("Conversation renamed!")
                                st.rerun()
                    
                    with col_cancel:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state.show_rename_dialog = False
                            st.rerun()
            
            # Circuit breaker and error status
            self._render_system_status()
    
    def render_chat_messages(self, messages: List[Dict]):
        """Render chat messages in the main interface"""
        try:
            for message in messages:
                role = message.get("role", "user")
                content = message.get("content", "")
                
                # Display message with appropriate styling
                with st.chat_message(role):
                    st.markdown(content)
        
        except Exception as e:
            self.logger.error(f"Error rendering messages: {e}")
            st.error("Error displaying conversation history")
    
    def render_welcome_message(self):
        """Render welcome message with templated prompt buttons"""
        config = self.config
        
        # Create welcome container with custom styling
        with st.container():
            # Welcome message
            st.markdown(f"""
            <div style="
                background-color: #f0f2f6;
                border: 1px solid #d1d5db;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            ">
                {config.ui.welcome_message}
            </div>
            """, unsafe_allow_html=True)
            
            # Prompt buttons
            st.markdown("**💡 Suggestions pour commencer :**")
            
            # Create columns for buttons
            cols = st.columns(len(config.ui.templated_prompts))
            
            for i, prompt_config in enumerate(config.ui.templated_prompts):
                with cols[i]:
                    # Create button with custom styling
                    button_label = f"{prompt_config['icon']} {prompt_config['title']}"
                    
                    if st.button(
                        button_label,
                        key=f"prompt_button_{prompt_config['id']}",
                        help=prompt_config['description'],
                        use_container_width=True
                    ):
                        # Process the templated prompt
                        self.conversation_manager.process_templated_prompt(prompt_config['prompt'])
                        st.rerun()
    
    def get_selected_collection(self) -> str:
        """Get the currently selected collection from session state"""
        config = self.config
        
        if "selected_collection" not in st.session_state:
            st.session_state.selected_collection = config.vectorstore.default_collection_key
        
        # Handle legacy collection names (migration from old format)
        legacy_mapping = {
            "Sub-chapters (Semantic)": "subchapters",
            "Original (Character-based)": "original"
        }
        
        # Check if current selection is a legacy format and migrate it
        if st.session_state.selected_collection in legacy_mapping:
            st.session_state.selected_collection = legacy_mapping[st.session_state.selected_collection]
        
        # Ensure the selected collection exists in current options
        collection_options = list(config.vectorstore.collections.keys())
        if st.session_state.selected_collection not in collection_options:
            st.session_state.selected_collection = config.vectorstore.default_collection_key
        
        return st.session_state.selected_collection
    
    def _filter_conversations(self, conversation_names: List[str], search_query: str) -> List[str]:
        """Filter conversations based on search query"""
        if not search_query:
            return conversation_names
        
        filtered = []
        search_lower = search_query.lower()
        
        for conv_name in conversation_names:
            # Search in conversation name
            if search_lower in conv_name.lower():
                filtered.append(conv_name)
                continue
            
            # TODO: Could also search in conversation content
            # This would require accessing conversation messages
        
        return filtered
    
    def _render_system_status(self):
        """Render system status indicators"""
        try:
            st.markdown("### 🔧 System Status")
            
            # Circuit breaker status (placeholder for now)
            st.info("🟢 System operational")
            
            # Add debug section if enabled
            config = self.config
            if config.debug:
                st.divider()
                st.subheader("🔧 Debug Tools")
                
                if st.button("Reset Session State", type="secondary"):
                    self.conversation_manager.reset_session_state()
                    st.success("Session state reset!")
                    st.rerun()
        
        except Exception as e:
            self.logger.error(f"Error rendering system status: {e}")
            st.error("System status unavailable")


# Global interface instance
_chat_interface: Optional[ChatInterface] = None


def get_chat_interface() -> ChatInterface:
    """Get the global chat interface instance"""
    global _chat_interface
    if _chat_interface is None:
        _chat_interface = ChatInterface()
    return _chat_interface


# Legacy compatibility functions
def get_langfuse_handler():
    """Get Langfuse handler (legacy compatibility)"""
    interface = get_chat_interface()
    return interface.get_langfuse_handler()


def create_stream_handler(placeholder):
    """Create stream handler (legacy compatibility)"""
    interface = get_chat_interface()
    return interface.create_stream_handler(placeholder)


def render_conversation_sidebar():
    """Render conversation sidebar (legacy compatibility)"""
    interface = get_chat_interface()
    interface.render_conversation_sidebar()


def render_chat_messages(messages):
    """Render chat messages (legacy compatibility)"""
    interface = get_chat_interface()
    interface.render_chat_messages(messages)


def render_welcome_message():
    """Render welcome message (legacy compatibility)"""
    interface = get_chat_interface()
    interface.render_welcome_message()


def get_selected_collection():
    """Get selected collection (legacy compatibility)"""
    interface = get_chat_interface()
    return interface.get_selected_collection()