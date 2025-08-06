"""
Test callback handlers functionality
"""

import pytest
from unittest.mock import Mock, patch
from langchain_core.documents import Document
from core.callbacks import RetrievalCallbackHandler, StreamlitCallbackHandler
from utils.chunks_display import ChunksCollector


class TestRetrievalCallbackHandler:
    """Test RetrievalCallbackHandler functionality"""
    
    def test_initialization_default(self):
        """Test handler initialization with defaults"""
        handler = RetrievalCallbackHandler()
        
        assert handler.memory is None
        assert handler.original_question is None
        assert isinstance(handler.chunks_collector, ChunksCollector)
        assert handler.retrieved_documents == []
        
    def test_initialization_with_collector(self):
        """Test handler initialization with custom collector"""
        collector = ChunksCollector()
        handler = RetrievalCallbackHandler(chunks_collector=collector)
        
        assert handler.chunks_collector is collector
        
    def test_on_retriever_start(self):
        """Test retriever start callback"""
        handler = RetrievalCallbackHandler()
        query = "What is emotivity?"
        
        with patch('builtins.print') as mock_print:
            handler.on_retriever_start({}, query)
            
        assert handler.original_question == query
        assert handler.chunks_collector.question == query
        mock_print.assert_called()
        
    def test_on_retriever_end(self):
        """Test retriever end callback"""
        handler = RetrievalCallbackHandler()
        
        documents = [
            Document(
                page_content="Test content 1",
                metadata={"source": "test1.pdf", "page": 1}
            ),
            Document(
                page_content="Test content 2",
                metadata={"source": "test2.pdf", "page": 2}
            )
        ]
        
        with patch('builtins.print') as mock_print:
            handler.on_retriever_end(documents)
            
        assert len(handler.retrieved_documents) == 2
        assert len(handler.chunks_collector.chunks) == 2
        mock_print.assert_called()
        
    def test_get_chunks_collector(self):
        """Test getting chunks collector"""
        collector = ChunksCollector()
        handler = RetrievalCallbackHandler(chunks_collector=collector)
        
        returned_collector = handler.get_chunks_collector()
        assert returned_collector is collector
        
    def test_get_retrieved_documents(self):
        """Test getting retrieved documents"""
        handler = RetrievalCallbackHandler()
        
        documents = [Document(page_content="test")]
        handler.on_retriever_end(documents)
        
        retrieved = handler.get_retrieved_documents()
        assert len(retrieved) == 1
        assert retrieved[0].page_content == "test"
        # Should return a copy, not the original
        assert retrieved is not handler.retrieved_documents


class TestStreamlitCallbackHandler:
    """Test StreamlitCallbackHandler functionality"""
    
    def test_initialization(self):
        """Test handler initialization"""
        placeholder = Mock()
        handler = StreamlitCallbackHandler(placeholder)
        
        assert handler.placeholder is placeholder
        assert handler.text == ""
        assert handler.counter == 0
        assert handler.total_tokens == 0
        
    def test_on_llm_start(self):
        """Test LLM start callback"""
        placeholder = Mock()
        handler = StreamlitCallbackHandler(placeholder)
        
        with patch('time.time', return_value=123.456):
            handler.on_llm_start({}, ["test prompt"])
            
        assert handler.llm_start_time == 123.456
        
    def test_on_llm_new_token(self):
        """Test new token callback"""
        placeholder = Mock()
        handler = StreamlitCallbackHandler(placeholder, update_every=1, delay=0)
        
        with patch('time.time', return_value=123.456):
            handler.on_llm_start({}, ["test"])
            handler.on_llm_new_token("Hello")
            
        assert handler.text == "Hello"
        assert handler.counter == 1
        assert handler.total_tokens == 1
        assert handler.first_token_time == 123.456
        placeholder.markdown.assert_called()
        
    def test_on_llm_end(self):
        """Test LLM end callback"""
        placeholder = Mock()
        handler = StreamlitCallbackHandler(placeholder, delay=0)
        
        with patch('time.time', side_effect=[100.0, 100.1, 100.5]):
            handler.on_llm_start({}, ["test"])
            handler.on_llm_new_token("Hello")
            handler.on_llm_end()
            
        # Should display final text without cursor
        placeholder.markdown.assert_called_with("Hello")
        assert handler.total_tokens == 1