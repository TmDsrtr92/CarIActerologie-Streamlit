"""
Test chunks display functionality
"""

import pytest
from unittest.mock import Mock, patch
from langchain_core.documents import Document
from services.ui_service.chunks_renderer import ChunksCollector, render_chunks_component, render_simple_chunks_list


class TestChunksCollector:
    """Test ChunksCollector functionality"""
    
    def test_chunks_collector_initialization(self):
        """Test ChunksCollector initialization"""
        collector = ChunksCollector()
        assert collector.chunks == []
        assert collector.question == ""
        assert collector.has_chunks() == False
        assert collector.get_chunk_count() == 0
        
    def test_set_question(self):
        """Test setting question"""
        collector = ChunksCollector()
        question = "What is emotivity?"
        collector.set_question(question)
        assert collector.question == question
        
    def test_add_chunks(self):
        """Test adding chunks"""
        collector = ChunksCollector()
        
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
        
        collector.add_chunks(documents)
        assert len(collector.chunks) == 2
        assert collector.has_chunks() == True
        assert collector.get_chunk_count() == 2
        
    def test_clear(self):
        """Test clearing collector"""
        collector = ChunksCollector()
        collector.set_question("test question")
        collector.add_chunks([Document(page_content="test")])
        
        collector.clear()
        assert collector.chunks == []
        assert collector.question == ""
        assert collector.has_chunks() == False
        
    @patch('streamlit.expander')
    @patch('streamlit.markdown') 
    def test_render_if_available_with_chunks(self, mock_markdown, mock_expander):
        """Test rendering when chunks are available"""
        collector = ChunksCollector()
        collector.set_question("test question")
        collector.add_chunks([Document(page_content="test content")])
        
        # Mock the expander context manager
        mock_expander.return_value.__enter__ = Mock()
        mock_expander.return_value.__exit__ = Mock()
        
        collector.render_if_available()
        mock_expander.assert_called_once()
        
    @patch('streamlit.expander')
    def test_render_if_available_no_chunks(self, mock_expander):
        """Test rendering when no chunks are available"""
        collector = ChunksCollector()
        
        collector.render_if_available()
        mock_expander.assert_not_called()


class TestChunksDisplay:
    """Test chunks display functions"""
    
    def create_sample_documents(self):
        """Create sample documents for testing"""
        return [
            Document(
                page_content="L'émotivité est une propriété fondamentale de la caractérologie.",
                metadata={
                    "source": "documents/traite.pdf",
                    "page": 45,
                    "section_title": "L'émotivité",
                    "section_type": "Section 1",
                    "chunk_size": 65
                }
            ),
            Document(
                page_content="L'activité détermine la tendance à l'action chez l'individu.",
                metadata={
                    "source": "documents/traite.pdf",
                    "page": 52,
                    "section_title": "L'activité", 
                    "section_type": "Section 2",
                    "chunk_size": 61
                }
            )
        ]
    
    @patch('streamlit.expander')
    @patch('streamlit.markdown')
    def test_render_chunks_component(self, mock_markdown, mock_expander):
        """Test chunks component rendering"""
        documents = self.create_sample_documents()
        question = "Qu'est-ce que l'émotivité ?"
        
        # Mock the expander context manager
        mock_expander.return_value.__enter__ = Mock()
        mock_expander.return_value.__exit__ = Mock()
        
        render_chunks_component(documents, question)
        
        # Should call expander with correct title
        expected_title = f"📚 Sources consultées ({len(documents)} chunks)"
        mock_expander.assert_called_with(expected_title, expanded=False)
        
        # Should call markdown multiple times (for styling, question, chunks, stats)
        assert mock_markdown.call_count >= 3
        
    @patch('streamlit.expander')
    def test_render_chunks_component_empty(self, mock_expander):
        """Test rendering with empty document list"""
        render_chunks_component([], "test question")
        mock_expander.assert_not_called()
        
    @patch('streamlit.expander')
    @patch('streamlit.write')
    def test_render_simple_chunks_list(self, mock_write, mock_expander):
        """Test simple chunks list rendering"""
        documents = self.create_sample_documents()
        
        # Mock the expander context manager
        mock_expander.return_value.__enter__ = Mock()
        mock_expander.return_value.__exit__ = Mock()
        
        render_simple_chunks_list(documents)
        
        # Should call expander and write
        mock_expander.assert_called_once()
        assert mock_write.call_count > 0