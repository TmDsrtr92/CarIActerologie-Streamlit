"""
Tests for LangGraph memory system
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from services.chat_service.memory_repository import MemoryRepository, get_memory_repository
# Legacy import removed - using microservice memory repository


class TestMemoryRepository:
    """Test memory repository"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_conversations.db")
    
    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_initialization(self):
        """Test memory repository initialization"""
        repo = MemoryRepository(db_path=self.db_path)
        
        assert repo.max_token_limit == 4000
        assert repo.model_name == "gpt-4o-mini"
        assert repo.db_path == self.db_path
        assert hasattr(repo, '_is_langgraph_memory')
        assert repo._is_langgraph_memory is True
        assert os.path.exists(self.db_path)
    
    def test_create_conversation(self):
        """Test conversation creation"""
        repo = MemoryRepository(db_path=self.db_path)
        
        thread_id = repo.create_conversation("Test Conversation")
        
        assert isinstance(thread_id, str)
        assert len(thread_id) > 0
        
        # Verify conversation exists in list
        summaries = repo.list_conversations()
        assert len(summaries) == 1
        assert summaries[0].title == "Test Conversation"
        assert summaries[0].message_count == 0
    
    def test_set_current_thread(self):
        """Test setting current thread"""
        manager = MemoryRepository(db_path=self.db_path)
        
        thread_id1 = manager.create_conversation("Conversation 1")
        thread_id2 = manager.create_conversation("Conversation 2")
        
        manager.set_current_thread(thread_id1)
        assert manager.current_thread_id == thread_id1
        
        manager.set_current_thread(thread_id2)
        assert manager.current_thread_id == thread_id2
    
    @patch('core.langgraph_memory.tiktoken')
    def test_add_message(self, mock_tiktoken):
        """Test adding messages to conversation"""
        # Mock tokenizer
        mock_encoding = Mock()
        mock_encoding.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
        mock_tiktoken.encoding_for_model.return_value = mock_encoding
        
        manager = MemoryRepository(db_path=self.db_path)
        thread_id = manager.create_conversation("Test Conversation")
        
        # Add human message
        manager.add_message("human", "Hello")
        
        # Add AI message
        manager.add_message("ai", "Hi there!")
        
        # Verify messages are stored
        messages = manager.get_messages()
        assert len(messages) == 2
        assert messages[0].content == "Hello"
        assert messages[1].content == "Hi there!"
        
        # Verify token counting
        assert mock_encoding.encode.call_count >= 2
    
    @patch('core.langgraph_memory.tiktoken')
    def test_token_limit_trimming(self, mock_tiktoken):
        """Test message trimming when token limit exceeded"""
        # Mock tokenizer to return high token counts
        mock_encoding = Mock()
        mock_encoding.encode.return_value = [1] * 1500  # 1500 tokens per message
        mock_tiktoken.encoding_for_model.return_value = mock_encoding
        
        manager = MemoryRepository(db_path=self.db_path, max_token_limit=4000)
        thread_id = manager.create_conversation("Test Conversation")
        
        # Add messages that exceed token limit (3 * 1500 = 4500 > 4000)
        manager.add_message("human", "Message 1")
        manager.add_message("ai", "Response 1")
        manager.add_message("human", "Message 2")
        manager.add_message("ai", "Response 2")
        manager.add_message("human", "Message 3")  # This should trigger trimming
        
        messages = manager.get_messages()
        
        # Should have trimmed some messages to stay within limit
        assert len(messages) < 5
        # Most recent messages should be kept
        assert messages[-1].content == "Message 3"
    
    def test_clear_conversation(self):
        """Test clearing conversation messages"""
        manager = MemoryRepository(db_path=self.db_path)
        thread_id = manager.create_conversation("Test Conversation")
        
        manager.add_message("human", "Hello")
        manager.add_message("ai", "Hi there!")
        
        assert len(manager.get_messages()) == 2
        
        manager.clear()
        
        assert len(manager.get_messages()) == 0
    
    def test_delete_conversation(self):
        """Test deleting conversation"""
        manager = MemoryRepository(db_path=self.db_path)
        
        thread_id1 = manager.create_conversation("Conversation 1")
        thread_id2 = manager.create_conversation("Conversation 2")
        
        manager.add_message("human", "Hello")
        
        # Verify conversation exists
        conversations = manager.list_conversations()
        assert len(conversations) == 2
        
        # Delete conversation
        manager.delete_conversation(thread_id1)
        
        # Verify conversation is deleted
        conversations = manager.list_conversations()
        assert len(conversations) == 1
        assert conversations[0]['thread_id'] == thread_id2
    
    def test_list_conversations(self):
        """Test listing all conversations"""
        manager = MemoryRepository(db_path=self.db_path)
        
        thread_id1 = manager.create_conversation("Conversation 1")
        thread_id2 = manager.create_conversation("Conversation 2")
        
        conversations = manager.list_conversations()
        
        assert len(conversations) == 2
        titles = [conv['title'] for conv in conversations]
        assert "Conversation 1" in titles
        assert "Conversation 2" in titles
    
    def test_get_conversation_summary(self):
        """Test getting conversation summary"""
        manager = MemoryRepository(db_path=self.db_path)
        thread_id = manager.create_conversation("Test Conversation")
        
        manager.add_message("human", "Hello")
        manager.add_message("ai", "Hi there!")
        
        summary = manager.get_conversation_summary(thread_id)
        
        assert summary['title'] == "Test Conversation"
        assert summary['message_count'] == 2
        assert 'created_at' in summary
        assert 'last_updated' in summary
    
    def test_get_token_count(self):
        """Test token counting functionality"""
        manager = MemoryRepository(db_path=self.db_path)
        thread_id = manager.create_conversation("Test Conversation")
        
        initial_count = manager.get_token_count()
        assert initial_count == 0
        
        with patch('core.langgraph_memory.tiktoken') as mock_tiktoken:
            mock_encoding = Mock()
            mock_encoding.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
            mock_tiktoken.encoding_for_model.return_value = mock_encoding
            
            manager.add_message("human", "Hello")
            
            token_count = manager.get_token_count()
            assert token_count > 0


class TestConversationMemory:
    """Test backward compatibility wrapper"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_conversations.db")
    
    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_initialization(self):
        """Test conversation memory wrapper initialization"""
        memory = ConversationMemory(db_path=self.db_path)
        
        assert hasattr(memory, 'manager')
        assert isinstance(memory.manager, MemoryRepository)
        assert hasattr(memory.manager, '_is_langgraph_memory')
    
    def test_backward_compatibility_methods(self):
        """Test backward compatibility methods"""
        memory = ConversationMemory(db_path=self.db_path)
        
        # Test chat_memory property
        assert hasattr(memory, 'chat_memory')
        
        # Test memory property  
        assert hasattr(memory, 'memory')
        
        # Test clear method
        memory.clear()  # Should not raise error
        
        # Test get_token_count method
        token_count = memory.get_token_count()
        assert isinstance(token_count, int)


class TestMemoryFactoryFunctions:
    """Test memory factory functions"""
    
    def test_create_langgraph_memory_manager(self):
        """Test creating LangGraph memory manager"""
        from services.chat_service.memory_repository import get_memory_repository
        
        manager = create_langgraph_memory_manager()
        
        assert isinstance(manager, MemoryRepository)
        assert hasattr(manager, '_is_langgraph_memory')
    
    def test_create_memory_manager(self):
        """Test creating backward compatible memory manager"""
        from services.chat_service.memory_repository import get_memory_repository
        
        memory = create_memory_manager()
        
        assert isinstance(memory, ConversationMemory)
        assert hasattr(memory, 'manager')
        assert isinstance(memory.manager, MemoryRepository)


if __name__ == "__main__":
    pytest.main([__file__])