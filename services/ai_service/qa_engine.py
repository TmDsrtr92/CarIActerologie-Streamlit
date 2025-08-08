"""
QA Engine - handles question answering operations.
Refactored from core/langgraph_qa_chain.py into a service-oriented architecture.
"""

from typing import Dict, Any, List, Optional, Callable
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
import time

from services.ai_service.models import RAGState, AIResponse, QARequest
from services.ai_service.llm_client import get_llm_client, get_vectorstore_client
from services.chat_service.memory_repository import get_memory_repository
from infrastructure.config.prompts import get_qa_prompt
from infrastructure.monitoring.logging_service import get_logger




class QAEngine:
    """
    Question-Answering engine using LangGraph for RAG workflow.
    Handles the complete QA pipeline from question to response.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.llm_client = get_llm_client()
        self.vectorstore_client = get_vectorstore_client()
        self.memory_repository = get_memory_repository()
        self._chain = None
    
    def get_qa_chain(self, memory_manager=None, collection_key: str = None):
        """
        Get compiled QA chain with memory and retrieval
        
        Args:
            memory_manager: Memory manager for conversation context
            collection_key: Key for vector store collection
            
        Returns:
            Compiled LangGraph chain
        """
        if self._chain is None:
            try:
                # Get LLM and retriever
                llm = self.llm_client.get_llm()
                retriever = self.vectorstore_client.get_retriever(collection_key)
                
                # Get QA prompt
                qa_prompt = get_qa_prompt()
                
                # Define workflow functions
                def retrieve_documents(state: RAGState) -> Dict[str, Any]:
                    """Retrieve relevant documents"""
                    try:
                        # Get chat history for context
                        chat_history = state.chat_history
                        question = state.question
                        
                        # Perform retrieval
                        documents = retriever.invoke(question)
                        
                        self.logger.debug(f"Retrieved {len(documents)} documents")
                        return {"context": documents}
                        
                    except Exception as e:
                        self.logger.error(f"Error retrieving documents: {e}")
                        return {"context": []}
                
                def generate_answer(state: RAGState) -> Dict[str, Any]:
                    """Generate answer using LLM"""
                    try:
                        # Prepare context from documents
                        context_text = "\n\n".join([doc.page_content for doc in state.context])
                        
                        # Format chat history
                        history_text = ""
                        if state.chat_history:
                            history_messages = []
                            for msg in state.chat_history[-6:]:  # Last 6 messages for context
                                role = "User" if isinstance(msg, HumanMessage) else "Assistant"
                                history_messages.append(f"{role}: {msg.content}")
                            history_text = "\n".join(history_messages)
                        
                        # Create prompt
                        formatted_prompt = qa_prompt.format(
                            context=context_text,
                            chat_history=history_text,
                            question=state.question
                        )
                        
                        # Generate response
                        response = llm.invoke([HumanMessage(content=formatted_prompt)])
                        answer = response.content
                        
                        # Create messages
                        messages = [
                            HumanMessage(content=state.question),
                            AIMessage(content=answer)
                        ]
                        
                        return {
                            "answer": answer,
                            "messages": messages
                        }
                        
                    except Exception as e:
                        self.logger.error(f"Error generating answer: {e}")
                        error_message = "Je suis désolé, mais j'ai rencontré une erreur lors du traitement de votre question. Pourriez-vous réessayer?"
                        return {
                            "answer": error_message,
                            "messages": [
                                HumanMessage(content=state.question),
                                AIMessage(content=error_message)
                            ]
                        }
                
                # Create workflow
                workflow = StateGraph(RAGState)
                
                # Add nodes
                workflow.add_node("retrieve", retrieve_documents)
                workflow.add_node("generate", generate_answer)
                
                # Define edges
                workflow.add_edge(START, "retrieve")
                workflow.add_edge("retrieve", "generate")
                workflow.add_edge("generate", END)
                
                # Set memory checkpointer if available
                checkpointer = None
                if memory_manager and hasattr(memory_manager, '_is_langgraph_memory'):
                    # Use simple memory saver for now
                    checkpointer = MemorySaver()
                
                # Compile chain
                self._chain = workflow.compile(checkpointer=checkpointer)
                
                self.logger.info("QA chain compiled successfully")
                
            except Exception as e:
                self.logger.error(f"Error compiling QA chain: {e}")
                raise
        
        return self._chain
    
    def process_question(self, request: QARequest, callbacks: List[Callable] = None) -> AIResponse:
        """
        Process a question and return AI response
        
        Args:
            request: QA request with question and context
            callbacks: Optional callbacks for streaming
            
        Returns:
            AI response with answer and metadata
        """
        start_time = time.time()
        
        try:
            # Get QA chain
            chain = self.get_qa_chain(collection_key=request.collection_key)
            
            # Prepare initial state
            initial_state = RAGState(
                question=request.question,
                chat_history=request.chat_history,
                messages=[],
                context=[],
                answer=""
            )
            
            # Configure chain execution
            config = {"configurable": {"thread_id": "default"}}
            if callbacks:
                config["callbacks"] = callbacks
            
            # Execute chain
            result = chain.invoke(initial_state, config=config)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create response
            response = AIResponse(
                answer=result["answer"],
                context_documents=result.get("context", []),
                processing_time=processing_time,
                metadata={
                    "question": request.question,
                    "collection_key": request.collection_key,
                    "message_count": len(result.get("messages", []))
                }
            )
            
            self.logger.info(f"Question processed successfully in {processing_time:.2f}s")
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing question: {e}")
            
            # Return error response
            return AIResponse(
                answer="Je suis désolé, mais j'ai rencontré une erreur lors du traitement de votre question. Pourriez-vous réessayer?",
                processing_time=time.time() - start_time,
                metadata={
                    "error": str(e),
                    "question": request.question,
                    "collection_key": request.collection_key
                }
            )
    
    def invoke(self, input_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Legacy invoke method for compatibility with existing code
        
        Args:
            input_data: Input containing question and other parameters
            config: Configuration including callbacks
            
        Returns:
            Result dictionary with answer
        """
        try:
            # Extract question
            question = input_data.get("question", "")
            if not question:
                raise ValueError("Question is required")
            
            # Create request
            request = QARequest(
                question=question,
                collection_key=input_data.get("collection_key"),
                chat_history=input_data.get("chat_history", [])
            )
            
            # Extract callbacks from config
            callbacks = []
            if config and "callbacks" in config:
                callbacks = config["callbacks"]
            
            # Process question
            response = self.process_question(request, callbacks)
            
            # Return in legacy format
            return {
                "answer": response.answer,
                "context": response.context_documents,
                "metadata": response.metadata
            }
            
        except Exception as e:
            self.logger.error(f"Error in legacy invoke: {e}")
            return {
                "answer": "Je suis désolé, mais j'ai rencontré une erreur lors du traitement de votre question. Pourriez-vous réessayer?",
                "context": [],
                "metadata": {"error": str(e)}
            }


# Global QA engine instance
_qa_engine: Optional[QAEngine] = None


def get_qa_engine() -> QAEngine:
    """Get the global QA engine instance"""
    global _qa_engine
    if _qa_engine is None:
        _qa_engine = QAEngine()
    return _qa_engine


# Legacy compatibility function
def setup_qa_chain_with_memory(memory_manager=None, collection_key: str = None):
    """
    Setup QA chain with memory (legacy compatibility)
    
    Args:
        memory_manager: Memory manager instance
        collection_key: Vector store collection key
        
    Returns:
        QA engine instance (behaves like a chain)
    """
    engine = get_qa_engine()
    engine.get_qa_chain(memory_manager, collection_key)
    return engine