import streamlit as st
from core.langgraph_qa_chain import setup_qa_chain_with_memory, clean_response
from utils.logging_config import initialize_logging, get_logger, log_user_interaction, get_error_tracker, log_execution_time
from utils.conversation_manager import (
    initialize_conversations, 
    get_current_messages, 
    add_message,
    get_current_memory,
    should_show_welcome_message,
    get_pending_prompt,
    get_current_conversation
)
from utils.streamlit_helpers import (
    get_langfuse_handler, 
    create_stream_handler, 
    render_conversation_sidebar, 
    render_chat_messages,
    render_welcome_message,
    get_selected_collection
)
from core.callbacks import RetrievalCallbackHandler

# Initialize logging and error tracking
error_tracker = initialize_logging()
logger = get_logger(__name__)

# Initialize the app
st.title("CarIActérologie")
logger.info("Application started")

# Initialize conversations
try:
    initialize_conversations()
    logger.info("Conversations initialized successfully")
except Exception as e:
    error_tracker.track_error(e, "conversation_initialization")
    st.error("Failed to initialize conversations. Please refresh the page.")

# Set up Langfuse handler
langfuse_handler = get_langfuse_handler()

# Render conversation sidebar
render_conversation_sidebar()

# Get current conversation messages and memory
messages = get_current_messages()
current_memory = get_current_memory()

# Get selected collection
selected_collection = get_selected_collection()

# Set up QA chain with memory and selected collection
qa_chain = setup_qa_chain_with_memory(current_memory, collection_key=selected_collection)

# Show welcome message if this is a new conversation
if should_show_welcome_message():
    render_welcome_message()

# Always render existing chat messages (if any)
if messages:
    render_chat_messages(messages)

# Check for pending prompt from welcome buttons
pending_prompt = get_pending_prompt()

# Determine which input to process
prompt_input = pending_prompt  # Only use pending prompt if it exists

if prompt_input:
    try:
        # Log user interaction
        log_user_interaction(
            logger, 
            "query_submitted", 
            query_length=len(prompt_input),
            conversation=get_current_conversation()
        )
        
        # Add user message to conversation
        add_message("user", prompt_input)
        
        # Display user message
        user_msg = st.chat_message("user")
        user_msg.markdown(prompt_input)

        # Create assistant message placeholder
        assistant_msg = st.chat_message("assistant")
        stream_placeholder = assistant_msg.empty()
        
        # Create streaming handler
        stream_handler = create_stream_handler(stream_placeholder)
        
        # Create retrieval callback handler with memory
        retrieval_handler = RetrievalCallbackHandler(memory=current_memory)

        # Get response from QA chain with streaming and memory
        logger_context = get_logger("qa_chain")
        with log_execution_time(logger_context, "qa_chain_invocation", query_length=len(prompt_input)):
            result = qa_chain.invoke(
                {"question": prompt_input},
                config={"callbacks": [langfuse_handler, stream_handler, retrieval_handler]}
            )
        
        answer = result["answer"]
        # Note: source_documents not available with memory-enabled chain

        # Clean the response to remove any repetition of the user's question
        cleaned_answer = clean_response(answer, prompt_input)

        # Display final response (remove cursor)
        stream_placeholder.markdown(cleaned_answer)

        # Add assistant message to conversation
        add_message("assistant", cleaned_answer)
        
        # Log successful response
        logger.info("Response generated successfully", extra={
            "response_length": len(cleaned_answer),
            "conversation": get_current_conversation()
        })
        
    except Exception as e:
        # Track and display error
        error_tracker.track_error(e, "qa_chain_execution", query=prompt_input)
        st.error("Sorry, I encountered an error processing your request. Please try again.")
        logger.error(f"Error processing query: {str(e)}", exc_info=True)

# Always show chat input at the end (this ensures it persists after templated prompts)
manual_prompt = st.chat_input("Comment puis-je t'aider aujourd'hui ?")
if manual_prompt:
    # Process manual input by setting it as pending and rerunning
    from utils.conversation_manager import set_pending_prompt
    set_pending_prompt(manual_prompt)
    st.rerun()
