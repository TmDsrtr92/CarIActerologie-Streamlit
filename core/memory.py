from langchain.memory import ConversationTokenBufferMemory
from langchain_core.messages import BaseMessage
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from config.settings import get_openai_api_key, MEMORY_CONFIG
import tiktoken

class ConversationMemory:
    """Manages conversation memory for each chat session using token-based buffer"""
    
    def __init__(self, max_token_limit: int = None):
        """
        Initialize conversation memory with token-based buffer
        
        Args:
            max_token_limit: Maximum number of tokens to keep in memory (default: from settings)
        """
        # Use settings or provided value
        if max_token_limit is None:
            max_token_limit = MEMORY_CONFIG["max_token_limit"]
        
        # Create LLM for token counting
        openai_api_key = get_openai_api_key()
        
        llm = ChatOpenAI(
            openai_api_key=openai_api_key,
            model_name=MEMORY_CONFIG["model_name"],
            temperature=0
        )
        
        # CORRECTION: Ajout de output_key pour une gestion correcte de la mémoire
        self.memory = ConversationTokenBufferMemory(
            llm=llm,
            max_token_limit=max_token_limit,
            return_messages=True,
            memory_key="chat_history",
            input_key="question",
            output_key="answer"  # Ajout de la clé de sortie
        )
        
        # Store the LLM for token counting
        self.llm = llm
        self.max_token_limit = max_token_limit
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]):
        """
        Save context to memory - méthode recommandée pour ConversationalRetrievalChain
        
        Args:
            inputs: Dictionary with input data (e.g., {"question": "user question"})
            outputs: Dictionary with output data (e.g., {"answer": "ai response"})
        """
        self.memory.save_context(inputs, outputs)
    
    
    def get_memory_variables(self) -> Dict[str, Any]:
        """Get memory variables for the LLM context"""
        return self.memory.load_memory_variables({})
    
    def clear(self):
        """Clear the conversation memory"""
        self.memory.clear()
    
    def get_chat_history(self) -> List[BaseMessage]:
        """Get the chat history as a list of messages"""
        return self.memory.chat_memory.messages
    
    def get_token_count(self) -> int:
        """Get current token count in memory"""
        try:
            # Get the current messages
            messages = self.get_chat_history()
            
            # Calculate total tokens from all messages
            total_tokens = 0
            for message in messages:
                # Count tokens in the message content
                if hasattr(message, 'content') and message.content:
                    # Use tiktoken for accurate token counting
                    encoding = tiktoken.encoding_for_model(MEMORY_CONFIG["model_name"])
                    tokens = encoding.encode(str(message.content))
                    total_tokens += len(tokens)
            
            return total_tokens
        except Exception:
            # Fallback: return message count as approximation
            return len(self.get_chat_history()) * 50  # Rough estimate

def create_memory_manager() -> ConversationMemory:
    """Create a new memory manager instance"""
    return ConversationMemory() 