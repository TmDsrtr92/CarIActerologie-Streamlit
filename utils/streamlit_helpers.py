import streamlit as st
import time
from langfuse.langchain import CallbackHandler
from config.settings import STREAMING_CONFIG
from config.welcome_config import WELCOME_MESSAGE, TEMPLATED_PROMPTS, WELCOME_STYLE, PROMPT_BUTTON_STYLE
from core.callbacks import StreamlitCallbackHandler


def get_langfuse_handler():
    """Get Langfuse callback handler if keys are configured, otherwise return None"""
    try:
        from config.app_config import get_config
        config = get_config()
        
        # Only initialize if both keys are available
        if config.api.langfuse_secret_key and config.api.langfuse_public_key:
            return CallbackHandler()
        else:
            return None
    except Exception:
        return None

def create_stream_handler(placeholder):
    """Create a streaming callback handler for Streamlit"""
    return StreamlitCallbackHandler(
        placeholder, 
        update_every=STREAMING_CONFIG["update_every"], 
        delay=STREAMING_CONFIG["delay"]
    )

def render_conversation_sidebar():
    """Render the conversation sidebar"""
    from utils.conversation_manager import (
        get_conversation_names, 
        get_current_conversation, 
        set_current_conversation, 
        create_new_conversation,
        get_current_memory,
        clear_conversation_memory,
        reset_session_state,
        update_conversation_title
    )
    from config.settings import MEMORY_CONFIG, AVAILABLE_COLLECTIONS, DEFAULT_COLLECTION_KEY
    
    conversation_names = get_conversation_names()
    current_conversation = get_current_conversation()
    
    # Get conversations data for title display
    from utils.conversation_manager import _get_user_conversations_key
    conversations_key = _get_user_conversations_key()
    
    with st.sidebar:
        # Enhanced sidebar header
        st.markdown("## 💬 Conversations")
        
        # Add conversation search
        search_query = st.text_input("🔍 Search conversations", placeholder="Search by title or content...")
        
        # Filter conversations based on search
        if search_query:
            filtered_conversations = _filter_conversations(conversation_names, search_query)
            display_conversations = filtered_conversations
            st.caption(f"🔍 {len(filtered_conversations)} of {len(conversation_names)} conversations")
        else:
            display_conversations = conversation_names
            st.caption(f"📊 {len(conversation_names)} conversation{'s' if len(conversation_names) != 1 else ''}")
        
        # Add filter options
        with st.expander("🎯 Filters", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                # Date filter
                date_filter = st.selectbox(
                    "📅 Date Range",
                    ["All", "Last 24 hours", "Last 7 days", "Last 30 days"],
                    help="Filter conversations by date"
                )
            
            with col2:
                # Sort options
                sort_option = st.selectbox(
                    "📈 Sort by",
                    ["Recent", "Oldest", "A-Z", "Z-A"],
                    help="Sort conversations"
                )
            
            # Apply filters and sorting
            display_conversations = _apply_filters_and_sorting(display_conversations, date_filter, sort_option)
        
        # Enhanced conversation selection with custom styling
        st.markdown("""
        <style>
        .conversation-item {
            padding: 0.5rem;
            margin: 0.25rem 0;
            border-radius: 0.5rem;
            border: 1px solid #e0e0e0;
            background: #f9f9f9;
        }
        .conversation-item:hover {
            background: #e3f2fd;
            border-color: #2196f3;
        }
        .active-conversation {
            background: #e3f2fd !important;
            border-color: #2196f3 !important;
            font-weight: bold;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Show filtered conversations or message if none found
        if display_conversations:
            # Ensure current conversation is in the display list, or select first one
            if current_conversation in display_conversations:
                selected_index = display_conversations.index(current_conversation)
            else:
                selected_index = 0
                
            # Create a format function that shows custom titles
            def format_conversation_name(conv_name):
                conversations = st.session_state.get(conversations_key, {})
                conv_data = conversations.get(conv_name, {})
                custom_title = conv_data.get("title", conv_name.title())
                return f"📄 {custom_title}"
            
            selected = st.radio(
                "Select a conversation:",
                display_conversations,
                index=selected_index,
                format_func=format_conversation_name
            )
            set_current_conversation(selected)
        else:
            st.info("🔍 No conversations match your search criteria")
            st.write("**Current conversation:**")
            st.write(f"📄 {current_conversation.title()}")
        
        # Add editable title for current conversation
        st.divider()
        st.write("**✏️ Edit Current Conversation**")
        
        # Get current conversation details
        conversations = st.session_state.get(conversations_key, {})
        current_conv_data = conversations.get(current_conversation, {})
        current_title = current_conv_data.get("title", current_conversation.title())
        
        # Title editing form
        with st.form(f"edit_title_{current_conversation}"):
            new_title = st.text_input(
                "Conversation Title",
                value=current_title,
                placeholder="Enter conversation title...",
                help="Give your conversation a meaningful name"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                save_title = st.form_submit_button("💾 Save", use_container_width=True)
            with col2:
                reset_title = st.form_submit_button("🔄 Reset", use_container_width=True)
            
            if save_title and new_title.strip():
                if update_conversation_title(current_conversation, new_title.strip()):
                    st.success("✅ Title updated!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Failed to update title")
            
            if reset_title:
                # Reset to default title format
                default_title = current_conversation.title()
                if update_conversation_title(current_conversation, default_title):
                    st.success("🔄 Title reset!")
                    time.sleep(0.5)
                    st.rerun()
        
        # Enhanced new conversation button
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("➕ New Conversation", use_container_width=True, type="primary"):
                with st.spinner("Creating new conversation..."):
                    create_new_conversation()
                st.success("✅ New conversation created!")
                time.sleep(0.5)
                st.rerun()
        
        with col2:
            # Add conversation management options
            if st.button("🗑️", help="Clear current conversation", use_container_width=True):
                if st.session_state.get("confirm_clear", False):
                    clear_conversation_memory()
                    st.success("Conversation cleared!")
                    st.session_state["confirm_clear"] = False
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.session_state["confirm_clear"] = True
                    st.warning("Click again to confirm clearing this conversation")
        
        # Show confirmation state
        if st.session_state.get("confirm_clear", False):
            st.error("⚠️ Click 🗑️ again to confirm deletion")
        
        # Collection selection section
        st.divider()
        st.subheader("📚 Collection de documents")
        
        # Get current collection from session state or use default
        if "selected_collection" not in st.session_state:
            st.session_state.selected_collection = DEFAULT_COLLECTION_KEY
        
        # Collection selector
        collection_options = list(AVAILABLE_COLLECTIONS.keys())
        current_index = collection_options.index(st.session_state.selected_collection)
        
        selected_collection = st.selectbox(
            "Type de chunking:",
            collection_options,
            index=current_index,
            help="Choisissez le type de découpage des documents"
        )
        
        # Update session state if selection changed
        if selected_collection != st.session_state.selected_collection:
            st.session_state.selected_collection = selected_collection
            st.rerun()
        
        # Display collection info
        collection_info = AVAILABLE_COLLECTIONS[selected_collection]
        st.write(f"**Description:** {collection_info['description']}")
        st.write(f"**Type:** {collection_info['chunk_type']}")
        
        # Collection status indicator
        if collection_info['chunk_type'] == 'semantic':
            st.success("✅ Chunking sémantique actif")
        else:
            st.info("ℹ️ Chunking par caractères actif")
        
        # Memory management section
        st.divider()
        st.subheader("🧠 Memory Management")
        
        current_memory = get_current_memory()
        chat_history = current_memory.get_chat_history()
        token_count = current_memory.get_token_count()
        max_tokens = MEMORY_CONFIG["max_token_limit"]
        
        # Display memory statistics
        st.write(f"**Messages:** {len(chat_history)}")
        st.write(f"**Tokens:** {token_count}/{max_tokens}")
        
        # Progress bar for token usage
        token_percentage = (token_count / max_tokens) * 100
        st.progress(token_percentage / 100)
        
        # Color-coded token status
        if token_percentage > 90:
            st.warning("⚠️ Memory nearly full")
        elif token_percentage > 70:
            st.info("ℹ️ Memory usage moderate")
        else:
            st.success("✅ Memory usage normal")
        
        if st.button("Clear Memory", type="secondary"):
            clear_conversation_memory()
            st.success("Memory cleared!")
            st.rerun()
        
        # Circuit breaker status section
        st.divider()
        st.subheader("🛡️ Service Status")
        
        try:
            from utils.retry_utils import get_openai_circuit_breaker
            circuit_breaker = get_openai_circuit_breaker()
            circuit_state = circuit_breaker.get_state()
            
            state = circuit_state["state"]
            failure_count = circuit_state["failure_count"]
            success_count = circuit_state["success_count"]
            remaining_timeout = circuit_state["remaining_timeout"]
            
            # Display circuit breaker status
            if state == "closed":
                st.success(f"✅ Service disponible")
                st.write(f"**Succès:** {success_count}")
            elif state == "open":
                st.error(f"🔴 Service indisponible")
                st.write(f"**Échecs consécutifs:** {failure_count}")
                if remaining_timeout > 0:
                    st.write(f"**Réessai dans:** {remaining_timeout:.0f}s")
            elif state == "half_open":
                st.warning(f"🟡 Test de récupération")
                st.write(f"**Échecs:** {failure_count}")
            
            # Offline mode guidance when service is down
            if state == "open":
                st.divider()
                st.subheader("📚 Mode Dégradé")
                
                # Show offline capabilities
                with st.expander("💡 Que puis-je faire ?", expanded=True):
                    from utils.fallback_responses import get_fallback_system
                    fallback_system = get_fallback_system()
                    guidance = fallback_system.get_offline_guidance()
                    st.markdown(guidance)
                
                # Quick access to common topics
                st.write("**🔍 Questions fréquentes disponibles :**")
                if st.button("📖 Qu'est-ce que la caractérologie ?", type="secondary"):
                    from utils.conversation_manager import set_pending_prompt
                    set_pending_prompt("Qu'est-ce que la caractérologie ?")
                    st.rerun()
                
                if st.button("📋 Quels sont les 8 types ?", type="secondary"):
                    from utils.conversation_manager import set_pending_prompt
                    set_pending_prompt("Quels sont les 8 types caractérologiques ?")
                    st.rerun()
                
                if st.button("🔍 Comment identifier mon type ?", type="secondary"):
                    from utils.conversation_manager import set_pending_prompt
                    set_pending_prompt("Comment puis-je identifier mon type de caractère ?")
                    st.rerun()
            
            # Manual reset option for admins (in debug mode)
            from config.app_config import get_config
            config = get_config()
            if config.debug and state == "open":
                st.divider()
                if st.button("🔧 Reset Circuit Breaker", type="secondary"):
                    circuit_breaker.reset()
                    st.success("Circuit breaker reset!")
                    st.rerun()
                    
        except Exception as e:
            st.error(f"Circuit breaker status unavailable: {e}")
        
        # Debug section (only in development)
        from config.app_config import get_config
        config = get_config()
        if config.debug:
            st.divider()
            st.subheader("🔧 Debug Tools")
            
            if st.button("Reset Session State", type="secondary"):
                reset_session_state()
                st.success("Session state reset!")
                st.rerun()
            
            # Show session state structure
            with st.expander("Session State Structure"):
                if st.checkbox("Show session state"):
                    st.json({
                        "conversations": {
                            name: {
                                "has_thread_id": "thread_id" in conv if isinstance(conv, dict) else False,
                                "message_count": len(conv.get("messages", [])) if isinstance(conv, dict) else len(conv) if isinstance(conv, list) else 0,
                                "type": type(conv).__name__
                            } for name, conv in st.session_state.get("conversations", {}).items()
                        },
                        "current_conversation": st.session_state.get("current_conversation", "None"),
                        "has_langgraph_manager": "langgraph_manager" in st.session_state
                    })
        
        # Show recent conversation context
        if chat_history:
            st.write("**Recent context:**")
            recent_messages = chat_history[-4:]  # Show last 4 messages
            for msg in recent_messages:
                role = "👤" if msg.type == "human" else "🤖"
                content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                st.write(f"{role} {content}")

def get_selected_collection():
    """Get the currently selected collection from session state"""
    from config.settings import DEFAULT_COLLECTION_KEY
    
    if "selected_collection" not in st.session_state:
        st.session_state.selected_collection = DEFAULT_COLLECTION_KEY
    
    return st.session_state.selected_collection


def _filter_conversations(conversation_names, search_query):
    """Filter conversations based on search query"""
    from utils.conversation_manager import _get_user_conversations_key
    import streamlit as st
    
    if not search_query:
        return conversation_names
    
    search_query = search_query.lower()
    filtered = []
    
    conversations_key = _get_user_conversations_key()
    conversations = st.session_state.get(conversations_key, {})
    
    for conv_name in conversation_names:
        conversation = conversations.get(conv_name, {})
        
        # Search in conversation name (key)
        if search_query in conv_name.lower():
            filtered.append(conv_name)
            continue
        
        # Search in custom conversation title (most important)
        custom_title = conversation.get("title", "")
        if search_query in custom_title.lower():
            filtered.append(conv_name)
            continue
        
        # Search in message content
        messages = conversation.get("messages", [])
        for message in messages:
            if search_query in message.get("content", "").lower():
                filtered.append(conv_name)
                break
    
    return filtered


def _apply_filters_and_sorting(conversation_names, date_filter, sort_option):
    """Apply date filters and sorting to conversations"""
    from utils.conversation_manager import _get_user_conversations_key
    from datetime import datetime, timedelta
    import streamlit as st
    
    conversations_key = _get_user_conversations_key()
    conversations = st.session_state.get(conversations_key, {})
    
    # Apply date filter
    if date_filter != "All":
        now = datetime.now()
        if date_filter == "Last 24 hours":
            cutoff = now - timedelta(hours=24)
        elif date_filter == "Last 7 days":
            cutoff = now - timedelta(days=7)
        elif date_filter == "Last 30 days":
            cutoff = now - timedelta(days=30)
        else:
            cutoff = None
        
        if cutoff:
            filtered_by_date = []
            for conv_name in conversation_names:
                conversation = conversations.get(conv_name, {})
                messages = conversation.get("messages", [])
                
                # Check if conversation has recent activity
                # For now, we'll use a simple heuristic - if it has messages, consider it recent
                # In a real implementation, you'd check actual timestamps
                if messages:  # Has activity
                    filtered_by_date.append(conv_name)
            
            conversation_names = filtered_by_date
    
    # Apply sorting
    if sort_option == "Recent":
        # Sort by most recent activity (conversations with more messages first)
        conversation_names = sorted(conversation_names, 
                                  key=lambda x: len(conversations.get(x, {}).get("messages", [])), 
                                  reverse=True)
    elif sort_option == "Oldest":
        # Sort by least recent activity
        conversation_names = sorted(conversation_names, 
                                  key=lambda x: len(conversations.get(x, {}).get("messages", [])))
    elif sort_option == "A-Z":
        conversation_names = sorted(conversation_names)
    elif sort_option == "Z-A":
        conversation_names = sorted(conversation_names, reverse=True)
    
    return conversation_names


def render_welcome_message():
    """
    Render welcome message with templated prompt buttons
    Handles button clicks by processing the selected prompt
    """
    from utils.conversation_manager import process_templated_prompt
    
    # Create welcome container with custom styling
    with st.container():
        # Welcome message
        st.markdown(f"""
        <div style="
            background-color: {WELCOME_STYLE['background_color']};
            border: 1px solid {WELCOME_STYLE['border_color']};
            border-radius: {WELCOME_STYLE['border_radius']};
            padding: {WELCOME_STYLE['padding']};
            margin-bottom: {WELCOME_STYLE['margin_bottom']};
        ">
            {WELCOME_MESSAGE}
        </div>
        """, unsafe_allow_html=True)
        
        # Prompt buttons
        st.markdown("**💡 Suggestions pour commencer :**")
        
        # Create columns for buttons
        cols = st.columns(len(TEMPLATED_PROMPTS))
        
        for i, prompt_config in enumerate(TEMPLATED_PROMPTS):
            with cols[i]:
                # Create button with custom styling
                button_label = f"{prompt_config['icon']} {prompt_config['title']}"
                
                if st.button(
                    button_label,
                    key=f"prompt_button_{prompt_config['id']}",
                    help=prompt_config['description'],
                    use_container_width=True
                ):
                    # Process the selected prompt
                    process_templated_prompt(prompt_config['prompt'])

def render_chat_messages(messages):
    """Render chat messages in the main area with enhanced visualization"""
    from datetime import datetime
    
    # Add minimal CSS for timestamps only
    st.markdown("""
    <style>
    .message-timestamp {
        font-size: 0.75rem;
        color: #888;
        margin-top: 0.5rem;
        text-align: right;
    }
    </style>
    """, unsafe_allow_html=True)
    
    if not messages:
        st.info("💬 No messages yet. Start a conversation!")
        return
    
    # Show message count
    st.caption(f"📝 {len(messages)} messages in this conversation")
    
    for i, message in enumerate(messages):
        role = message["role"]
        content = message["content"]
        
        # Add timestamp if available, otherwise use message index
        timestamp = message.get("timestamp")
        if not timestamp:
            # Generate a mock timestamp for display (could be enhanced with real timestamps)
            base_time = datetime.now()
            timestamp = base_time.strftime("%H:%M:%S")
        
        with st.chat_message(role):
            # Display message content normally
            st.markdown(content)
            
            # Add timestamp below message
            if role == "user":
                st.markdown(f'<div class="message-timestamp">👤 You • {timestamp}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="message-timestamp">🤖 Assistant • {timestamp}</div>', unsafe_allow_html=True) 