"""
Tests for LangGraph QA chain system
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from services.ai_service.qa_engine import (
    get_qa_engine
)
from services.ai_service.models import RAGState
from services.chat_service.memory_repository import get_memory_repository
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage



class TestRAGState:
    """Test RAG state model"""
    
    def test_rag_state_initialization(self):
        """Test RAG state initialization"""
        state = RAGState()
        
        assert state.messages == []
        assert state.question == ""
        assert state.context == []
        assert state.answer == ""
        assert state.chat_history == []
    
    def test_rag_state_with_data(self):
        """Test RAG state with data"""
        messages = [HumanMessage(content="Hello")]
        context = [Document(page_content="Test content")]
        
        state = RAGState(
            messages=messages,
            question="Test question",
            context=context,
            answer="Test answer"
        )
        
        assert state.messages == messages
        assert state.question == "Test question"
        assert state.context == context
        assert state.answer == "Test answer"


class TestLangGraphRAGChain:
    """Test LangGraph RAG chain"""
    
    def setup_method(self):
        """Set up test environment"""
        self.mock_memory = Mock(spec=LangGraphMemoryManager)
        self.mock_memory._is_langgraph_memory = True
    
    @patch('core.langgraph_qa_chain.setup_llm')
    @patch('core.langgraph_qa_chain.setup_retriever')
    def test_initialization(self, mock_setup_retriever, mock_setup_llm):
        """Test RAG chain initialization"""
        mock_llm = Mock()
        mock_retriever = Mock()
        mock_setup_llm.return_value = mock_llm
        mock_setup_retriever.return_value = mock_retriever
        
        chain = LangGraphRAGChain(
            memory_manager=self.mock_memory,
            collection_key="test_collection"
        )
        
        assert chain.memory_manager == self.mock_memory
        assert chain.llm == mock_llm
        assert chain.retriever == mock_retriever
        assert chain.prompt_name == "caracterologie_qa"
        assert chain.prompt_version is None
        
        # Verify setup calls
        mock_setup_llm.assert_called_once()
        mock_setup_retriever.assert_called_once_with("test_collection")
    
    @patch('core.langgraph_qa_chain.setup_llm')
    @patch('core.langgraph_qa_chain.setup_retriever')
    def test_build_workflow(self, mock_setup_retriever, mock_setup_llm):
        """Test workflow building"""
        chain = LangGraphRAGChain(memory_manager=self.mock_memory)
        
        # Workflow should be built during initialization
        assert hasattr(chain, 'workflow')
        assert hasattr(chain, 'app')
        assert chain.app is not None
    
    @patch('core.langgraph_qa_chain.setup_llm')
    @patch('core.langgraph_qa_chain.setup_retriever')
    def test_retrieve_context(self, mock_setup_retriever, mock_setup_llm):
        """Test context retrieval"""
        # Setup mocks
        mock_docs = [
            Document(page_content="Test content 1"),
            Document(page_content="Test content 2")
        ]
        mock_retriever = Mock()
        mock_retriever.invoke.return_value = mock_docs
        mock_setup_retriever.return_value = mock_retriever
        
        chain = LangGraphRAGChain(memory_manager=self.mock_memory)
        
        # Test retrieval
        state = RAGState(question="Test question")
        result = chain._retrieve_context(state)
        
        assert "context" in result
        assert len(result["context"]) == 2
        assert result["context"] == mock_docs
        
        mock_retriever.invoke.assert_called_once_with("Test question")
    
    @patch('core.langgraph_qa_chain.setup_llm')
    @patch('core.langgraph_qa_chain.setup_retriever')
    @patch('core.langgraph_qa_chain.get_qa_prompt')
    def test_contextualize_question(self, mock_get_prompt, mock_setup_retriever, mock_setup_llm):
        """Test question contextualization"""
        # Setup mocks
        mock_prompt = Mock()
        mock_prompt.format.return_value = "Contextualized question"
        mock_get_prompt.return_value = mock_prompt
        
        chain = LangGraphRAGChain(memory_manager=self.mock_memory)
        
        # Mock memory manager methods
        self.mock_memory.get_messages.return_value = [
            HumanMessage(content="Previous question"),
            AIMessage(content="Previous answer")
        ]
        
        state = RAGState(
            question="Current question",
            context=[Document(page_content="Context")]
        )
        
        result = chain._contextualize_question(state)
        
        # Should have chat history and potentially modified question
        assert "chat_history" in result
        assert len(result["chat_history"]) == 2
    
    @patch('core.langgraph_qa_chain.setup_llm')
    @patch('core.langgraph_qa_chain.setup_retriever')
    @patch('core.langgraph_qa_chain.get_qa_prompt')
    def test_generate_answer(self, mock_get_prompt, mock_setup_retriever, mock_setup_llm):
        """Test answer generation"""
        # Setup mocks
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="Generated answer")
        mock_setup_llm.return_value = mock_llm
        
        mock_prompt = Mock()
        mock_prompt.format.return_value = "Formatted prompt"
        mock_get_prompt.return_value = mock_prompt
        
        chain = LangGraphRAGChain(memory_manager=self.mock_memory)
        
        state = RAGState(
            question="Test question",
            context=[Document(page_content="Context")],
            chat_history=[]
        )
        
        result = chain._generate_answer(state)
        
        assert "answer" in result
        assert result["answer"] == "Generated answer"
        
        # Verify LLM was called
        mock_llm.invoke.assert_called_once()
    
    @patch('core.langgraph_qa_chain.setup_llm')
    @patch('core.langgraph_qa_chain.setup_retriever')
    def test_invoke_workflow(self, mock_setup_retriever, mock_setup_llm):
        """Test full workflow invocation"""
        # Setup comprehensive mocks
        mock_docs = [Document(page_content="Test context")]
        mock_retriever = Mock()
        mock_retriever.invoke.return_value = mock_docs
        mock_setup_retriever.return_value = mock_retriever
        
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="Test answer")
        mock_setup_llm.return_value = mock_llm
        
        # Mock memory manager
        self.mock_memory.get_messages.return_value = []
        self.mock_memory.add_message = Mock()
        
        # Mock prompt
        with patch('core.langgraph_qa_chain.get_qa_prompt') as mock_get_prompt:
            mock_prompt = Mock()
            mock_prompt.format.return_value = "Formatted prompt"
            mock_get_prompt.return_value = mock_prompt
            
            chain = LangGraphRAGChain(memory_manager=self.mock_memory)
            
            # Invoke the workflow
            result = chain.invoke({"question": "Test question"})
            
            assert "answer" in result
            
            # Verify memory was updated
            assert self.mock_memory.add_message.call_count == 2  # human + ai messages


class TestSetupFunctions:
    """Test setup functions"""
    
    def test_setup_langgraph_qa_chain(self):
        """Test LangGraph QA chain setup"""
        mock_memory = Mock(spec=LangGraphMemoryManager)
        mock_memory._is_langgraph_memory = True
        
        with patch('core.langgraph_qa_chain.LangGraphRAGChain') as mock_chain_class:
            mock_chain = Mock()
            mock_chain_class.return_value = mock_chain
            
            result = setup_langgraph_qa_chain(
                memory_manager=mock_memory,
                collection_key="test_collection"
            )
            
            assert result == mock_chain
            mock_chain_class.assert_called_once_with(
                mock_memory, "test_collection", "caracterologie_qa", None
            )
    
    def test_setup_qa_chain_with_memory_langgraph_wrapper(self):
        """Test QA chain setup with LangGraph memory wrapper"""
        # Mock memory wrapper
        mock_wrapper = Mock()
        mock_manager = Mock(spec=LangGraphMemoryManager)
        mock_manager._is_langgraph_memory = True
        mock_wrapper.manager = mock_manager
        
        with patch('core.langgraph_qa_chain.setup_langgraph_qa_chain') as mock_setup:
            mock_chain = Mock()
            mock_setup.return_value = mock_chain
            
            result = setup_qa_chain_with_memory(
                memory=mock_wrapper,
                collection_key="test_collection"
            )
            
            assert result == mock_chain
            mock_setup.assert_called_once_with(
                mock_manager, "test_collection", "caracterologie_qa", None
            )
    
    def test_setup_qa_chain_with_memory_direct_manager(self):
        """Test QA chain setup with direct LangGraph manager"""
        mock_manager = Mock(spec=LangGraphMemoryManager)
        mock_manager._is_langgraph_memory = True
        
        with patch('core.langgraph_qa_chain.setup_langgraph_qa_chain') as mock_setup:
            mock_chain = Mock()
            mock_setup.return_value = mock_chain
            
            result = setup_qa_chain_with_memory(
                memory=mock_manager,
                collection_key="test_collection"
            )
            
            assert result == mock_chain
            mock_setup.assert_called_once_with(
                mock_manager, "test_collection", "caracterologie_qa", None
            )
    
    def test_setup_qa_chain_with_memory_unsupported_type(self):
        """Test QA chain setup with unsupported memory type"""
        unsupported_memory = Mock()
        # Remove the _is_langgraph_memory attribute to make it unsupported
        if hasattr(unsupported_memory, '_is_langgraph_memory'):
            delattr(unsupported_memory, '_is_langgraph_memory')
        
        with pytest.raises(ValueError, match="Unsupported memory type"):
            setup_qa_chain_with_memory(memory=unsupported_memory)


if __name__ == "__main__":
    pytest.main([__file__])