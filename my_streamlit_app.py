import streamlit as st
from core.langgraph_qa_chain import setup_qa_chain_with_memory, clean_response
# Import OpenAI exceptions for specific error handling
import openai
from utils.logging_config import initialize_logging, get_logger, log_user_interaction, get_error_tracker, log_execution_time
from utils.retry_utils import retry_with_circuit_breaker, RetryStatus, CircuitBreakerError, get_openai_circuit_breaker
from utils.fallback_responses import generate_fallback_response, get_fallback_system
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
from utils.chunks_display import ChunksCollector
from auth.streamlit_auth import get_auth
from config.app_config import get_config

# Initialize logging and error tracking
error_tracker = initialize_logging()
logger = get_logger(__name__)

# Get configuration
config = get_config()

# Initialize authentication
auth = get_auth()

def main_app():
    """Main application content (protected by authentication)"""
    # Add responsive CSS for mobile devices
    st.markdown("""
    <style>
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        /* Adjust chat input for mobile */
        .stChatInput {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            background: white;
            padding: 0.5rem;
            border-top: 1px solid #e0e0e0;
        }
        
        /* Adjust chat messages for mobile */
        .stChatMessage {
            margin-bottom: 0.5rem;
        }
        
        /* Improve sidebar for mobile */
        .css-1d391kg {
            width: 100% !important;
        }
    }
    
    /* Improve overall layout */
    .main-header {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid #e3f2fd;
        margin-bottom: 1rem;
    }
    
    /* Enhanced chat input styling */
    .stChatInput > div {
        border-radius: 25px;
        border: 2px solid #e3f2fd;
    }
    
    .stChatInput > div:focus-within {
        border-color: #2196f3;
        box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize the app with enhanced header
    st.markdown('<div class="main-header"><h1>🧠 CarIActérologie</h1><p>AI-powered Characterology Assistant</p></div>', unsafe_allow_html=True)
    logger.info("Application started")

    # Initialize conversations with loading state
    try:
        with st.status("Initializing conversations...", expanded=False) as status:
            initialize_conversations()
            status.update(label="✅ Conversations loaded", state="complete")
        logger.info("Conversations initialized successfully")
    except Exception as e:
        error_tracker.track_error(e, "conversation_initialization")
        st.error("Failed to initialize conversations. Please refresh the page.")
        return

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
    with st.spinner(f"Setting up AI system with {selected_collection} collection..."):
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
        # Initialize variables at the top to avoid UnboundLocalError in exception handlers
        retry_status = RetryStatus()
        chunks_collector = ChunksCollector()
        
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
            
            # Show enhanced loading indicator with status
            with stream_placeholder.container():
                loading_status = st.status("🤔 Analyzing your question...", expanded=False)
                with loading_status:
                    st.write("🔍 Processing query...")
                    st.write("📚 Searching knowledge base...")
                    st.write("🧠 Generating response...")
            
            # Create streaming handler
            stream_handler = create_stream_handler(stream_placeholder)
            
            # Create retrieval callback handler with memory and chunks collector
            retrieval_handler = RetrievalCallbackHandler(memory=current_memory, chunks_collector=chunks_collector)

            # Set up retry status placeholder for user feedback
            retry_status_placeholder = stream_placeholder  # Use same placeholder for retry messages
            
            def execute_qa_chain_with_feedback():
                """Execute QA chain with user feedback during retries"""
                def qa_chain_call():
                    logger_context = get_logger("qa_chain")
                    with log_execution_time(logger_context, "qa_chain_invocation", query_length=len(prompt_input)):
                        # Build callback list, excluding None handlers
                        callbacks = [stream_handler, retrieval_handler]
                        if langfuse_handler is not None:
                            callbacks.insert(0, langfuse_handler)
                        
                        return qa_chain.invoke(
                            {"question": prompt_input},
                            config={"callbacks": callbacks}
                        )
                
                def on_retry_callback(attempt: int, error: Exception):
                    """Show retry status to user"""
                    from utils.retry_utils import exponential_backoff_delay
                    next_delay = exponential_backoff_delay(attempt - 1)  # attempt is 1-indexed in callback
                    
                    retry_status.on_retry_attempt(attempt, error, next_delay)
                    retry_message = retry_status.get_status_message()
                    
                    # Show retry message to user
                    retry_status_placeholder.markdown(retry_message)
                    
                    # Brief pause to show the message
                    import time
                    time.sleep(0.5)
                
                # Start retry tracking
                retry_status.start_retry(max_attempts=3)
                
                # Execute with retry logic and circuit breaker protection
                return retry_with_circuit_breaker(
                    qa_chain_call,
                    max_retries=3,
                    base_delay=1.0,
                    max_delay=30.0,
                    circuit_breaker=None,  # Use global OpenAI circuit breaker
                    on_retry=on_retry_callback
                )
            
            # Execute QA chain with retry and feedback
            result = execute_qa_chain_with_feedback()
            retry_status.finish_retry(success=True)
            
            answer = result["answer"]
            # Note: source_documents not available with memory-enabled chain

            # Clean the response to remove any repetition of the user's question
            cleaned_answer = clean_response(answer, prompt_input)

            # Display final response (remove cursor and any retry messages)
            stream_placeholder.markdown(cleaned_answer)
            
            # Display retrieved chunks component after the answer
            chunks_collector.render_if_available()

            # Add assistant message to conversation
            add_message("assistant", cleaned_answer)
            
            # Log successful response
            logger.info("Response generated successfully", extra={
                "response_length": len(cleaned_answer),
                "conversation": get_current_conversation()
            })
            
        except CircuitBreakerError as e:
            # Circuit breaker is open - provide graceful degradation with fallback response
            retry_status.finish_retry(success=False)
            error_tracker.track_error(e, "circuit_breaker_open", query=prompt_input)
            
            # Get circuit breaker status for context
            circuit_state = get_openai_circuit_breaker().get_state()
            remaining_time = circuit_state.get("remaining_timeout", 0)
            
            # Generate meaningful fallback response instead of just an error
            try:
                # Determine user level (could be enhanced with user preferences)
                user_level = "beginner"  # Default, could be made configurable
                
                # Generate contextual fallback response
                fallback_content = generate_fallback_response(prompt_input, user_level)
                
                # Add service status information
                fallback_system = get_fallback_system()
                status_message = fallback_system.get_service_status_message(circuit_state)
                
                # Create complete response with service info
                complete_response = f"""
{status_message}

{fallback_content}

---

🔄 **Récupération automatique** - Le service sera testé automatiquement dans {remaining_time:.0f} secondes.
                """.strip()
                
                # Display fallback response in chat format (not as error)
                stream_placeholder.markdown(complete_response)
                
                # Display chunks if any were retrieved before the circuit breaker opened
                chunks_collector.render_if_available()
                
                # Add fallback message to conversation history  
                add_message("assistant", complete_response)
                
                logger.info(f"Provided fallback response for circuit breaker open (question: {prompt_input[:50]}...)")
                
            except Exception as fallback_error:
                # If fallback system also fails, show simple error
                logger.error(f"Fallback system failed: {fallback_error}")
                st.error(f"⚠️ **Service temporairement indisponible** - Réessayez dans {remaining_time:.0f} secondes.")
            
            logger.warning(f"Circuit breaker open, fallback provided: {str(e)}")
            
        except openai.RateLimitError as e:
            # Rate limit exceeded after all retries
            retry_status.finish_retry(success=False)
            error_tracker.track_error(e, "rate_limit_error_final", query=prompt_input)
            st.error("🐌 **Limite de taux persistante** - Malgré plusieurs tentatives, le service est toujours surchargé. Veuillez attendre quelques minutes avant de réessayer.")
            logger.warning(f"Rate limit error after retries: {str(e)}")
            
        except openai.APIConnectionError as e:
            # Network/connection issues after all retries
            retry_status.finish_retry(success=False)
            error_tracker.track_error(e, "api_connection_error_final", query=prompt_input)
            st.error("🌐 **Problème de connexion persistant** - Impossible de joindre le service après plusieurs tentatives. Vérifiez votre connexion internet et réessayez plus tard.")
            logger.error(f"API connection error after retries: {str(e)}")
            
        except openai.APITimeoutError as e:
            # Request timeout after all retries
            retry_status.finish_retry(success=False)
            error_tracker.track_error(e, "api_timeout_error_final", query=prompt_input)
            st.error("⏱️ **Délais d'attente persistants** - Les requêtes prennent trop de temps malgré plusieurs tentatives. Essayez avec une question plus courte ou réessayez plus tard.")
            logger.warning(f"API timeout error after retries: {str(e)}")
            
        except openai.InternalServerError as e:
            # OpenAI server issues after all retries
            retry_status.finish_retry(success=False)
            error_tracker.track_error(e, "server_error_final", query=prompt_input)
            st.error("🔧 **Erreur serveur persistante** - Le service OpenAI rencontre des difficultés techniques prolongées. Veuillez réessayer dans quelques minutes.")
            logger.error(f"OpenAI server error after retries: {str(e)}")
            
        except openai.AuthenticationError as e:
            # API key issues (not retried)
            error_tracker.track_error(e, "authentication_error", query=prompt_input)
            st.error("🔑 **Erreur d'authentification** - Problème avec la clé API OpenAI. Veuillez contacter l'administrateur.")
            logger.error(f"Authentication error: {str(e)}")
            
        except openai.BadRequestError as e:
            # Invalid request - likely user input issue (not retried)
            error_tracker.track_error(e, "bad_request_error", query=prompt_input)
            st.error("❌ **Requête invalide** - Votre question n'a pas pu être traitée. Essayez de la reformuler différemment.")
            logger.warning(f"Bad request error: {str(e)}")
            
        except openai.ContentFilterFinishReasonError as e:
            # Content filtered by OpenAI (not retried)
            error_tracker.track_error(e, "content_filter_error", query=prompt_input)
            st.error("🚫 **Contenu filtré** - Votre question ou la réponse générée a été bloquée par les filtres de contenu. Essayez de reformuler votre question.")
            logger.warning(f"Content filter error: {str(e)}")
            
        except Exception as e:
            # Catch-all for any other unexpected errors
            retry_status.finish_retry(success=False)
            error_tracker.track_error(e, "qa_chain_execution", query=prompt_input)
            st.error("🔧 **Erreur inattendue** - Une erreur technique s'est produite. Veuillez réessayer ou actualiser la page.")
            logger.error(f"Unexpected error processing query: {str(e)}", exc_info=True)

    # Always show chat input at the end (this ensures it persists after templated prompts)
    manual_prompt = st.chat_input("Comment puis-je t'aider aujourd'hui ?")
    if manual_prompt:
        # Process manual input by setting it as pending and rerunning
        from utils.conversation_manager import set_pending_prompt
        set_pending_prompt(manual_prompt)
        st.rerun()


# Apply authentication wrapper
if config.auth.enabled:
    # Render user menu in sidebar if authenticated
    current_session = auth.get_current_session()
    if current_session:
        auth.render_user_menu()
    
    # Apply authentication requirement
    auth.require_authentication(main_app)
    
    # Render user settings dialog if needed
    auth.render_user_settings()
else:
    # Authentication disabled, run main app directly
    main_app()
