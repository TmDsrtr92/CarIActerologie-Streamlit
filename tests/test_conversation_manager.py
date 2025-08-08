"""
Tests for conversation manager
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from services.chat_service.conversation_manager import (
    ConversationManager, 
    get_conversation_manager,
    # Legacy compatibility functions
    initialize_conversations,
    get_conversation_names,
    get_current_conversation,
    set_current_conversation,
    get_current_messages,
    get_current_memory,
    add_message,
    create_new_conversation,
    clear_conversation_memory,
    should_show_welcome_message,
    set_pending_prompt,
    get_pending_prompt,
    process_templated_prompt
)


class MockSessionState:
    """Mock Streamlit session state for testing"""
    
    def __init__(self):
        self.data = {}
    
    def __contains__(self, key):
        return key in self.data
    
    def __getitem__(self, key):
        return self.data[key]
    
    def __setitem__(self, key, value):
        self.data[key] = value
    
    def get(self, key, default=None):
        return self.data.get(key, default)


class TestConversationManager:
    """Test conversation manager functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        # Mock streamlit session state
        self.mock_session_state = MockSessionState()
        
        # Mock streamlit module
        self.mock_st = Mock()
        self.mock_st.session_state = self.mock_session_state
        
        # Patch streamlit import
        self.st_patcher = patch.dict('sys.modules', {'streamlit': self.mock_st})
        self.st_patcher.start()
    
    def teardown_method(self):
        """Clean up test environment"""
        self.st_patcher.stop()
    
    @patch('services.chat_service.memory_repository.create_langgraph_memory_manager')
    @patch('services.chat_service.memory_repository.create_memory_manager')
    def test_initialize_conversations(self, mock_create_memory, mock_create_langgraph):
        """Test conversation initialization"""
        # Setup mocks
        mock_manager = Mock()
        mock_manager.create_conversation.return_value = "test-thread-id"
        mock_create_langgraph.return_value = mock_manager
        
        mock_memory = Mock()
        mock_create_memory.return_value = mock_memory
        
        # Initialize conversations
        initialize_conversations()
        
        # Verify session state setup
        assert "langgraph_manager" in self.mock_session_state
        assert "conversations" in self.mock_session_state
        assert "current_conversation" in self.mock_session_state
        assert "pending_prompt" in self.mock_session_state
        
        # Verify conversation structure
        conversations = self.mock_session_state["conversations"]
        assert "conversation 1" in conversations
        
        conversation = conversations["conversation 1"]
        assert conversation["thread_id"] == "test-thread-id"
        assert conversation["title"] == "Conversation 1"
        assert conversation["messages"] == []
        assert conversation["welcome_shown"] is False
        assert conversation["memory_manager"] == mock_memory
        
        # Verify current conversation is set
        assert self.mock_session_state["current_conversation"] == "conversation 1"
        
        # Verify LangGraph manager called
        mock_manager.create_conversation.assert_called_once_with("Conversation 1")
        mock_manager.set_current_thread.assert_called_once_with("test-thread-id")
    
    def test_get_conversation_names(self):
        """Test getting conversation names"""
        self.mock_session_state["conversations"] = {
            "conversation 1": {},
            "conversation 2": {},
            "test conversation": {}
        }
        
        names = get_conversation_names()
        
        assert len(names) == 3
        assert "conversation 1" in names
        assert "conversation 2" in names
        assert "test conversation" in names
    
    def test_get_current_conversation(self):
        """Test getting current conversation"""
        self.mock_session_state["current_conversation"] = "test conversation"
        
        current = get_current_conversation()
        
        assert current == "test conversation"
    
    def test_set_current_conversation(self):
        """Test setting current conversation"""
        # Setup conversations
        self.mock_session_state["conversations"] = {
            "conversation 1": {"thread_id": "thread-1"},
            "conversation 2": {"thread_id": "thread-2"}
        }
        
        # Mock LangGraph manager
        mock_manager = Mock()
        self.mock_session_state["langgraph_manager"] = mock_manager
        
        set_current_conversation("conversation 2")
        
        assert self.mock_session_state["current_conversation"] == "conversation 2"
        mock_manager.set_current_thread.assert_called_once_with("thread-2")
    
    def test_set_current_conversation_invalid(self):
        """Test setting invalid current conversation"""
        self.mock_session_state["conversations"] = {
            "conversation 1": {"thread_id": "thread-1"}
        }
        
        mock_manager = Mock()
        self.mock_session_state["langgraph_manager"] = mock_manager
        
        # Should not change anything for invalid conversation
        set_current_conversation("nonexistent")
        
        mock_manager.set_current_thread.assert_not_called()
    
    def test_get_current_messages(self):
        """Test getting current messages"""
        self.mock_session_state["current_conversation"] = "conversation 1"
        self.mock_session_state["conversations"] = {
            "conversation 1": {
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"}
                ]
            }
        }
        
        messages = get_current_messages()
        
        assert len(messages) == 2
        assert messages[0]["content"] == "Hello"
        assert messages[1]["content"] == "Hi there!"
    
    def test_get_current_memory(self):
        """Test getting current memory"""
        # Setup conversation
        mock_memory = Mock()
        mock_manager = Mock()
        
        self.mock_session_state["current_conversation"] = "conversation 1"
        self.mock_session_state["conversations"] = {
            "conversation 1": {
                "thread_id": "thread-1",
                "memory_manager": mock_memory
            }
        }
        self.mock_session_state["langgraph_manager"] = mock_manager
        
        memory = get_current_memory()
        
        assert memory == mock_memory
        mock_manager.set_current_thread.assert_called_once_with("thread-1")
        
        # Test memory manager thread update
        mock_memory.manager = Mock()
        memory = get_current_memory()
        mock_memory.manager.set_current_thread.assert_called_once_with("thread-1")
    
    def test_add_message(self):
        """Test adding message to conversation"""
        self.mock_session_state["current_conversation"] = "conversation 1"
        self.mock_session_state["conversations"] = {
            "conversation 1": {"messages": []}
        }
        
        add_message("user", "Hello world")
        
        messages = self.mock_session_state["conversations"]["conversation 1"]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello world"
    
    @patch('services.chat_service.memory_repository.create_memory_manager')
    def test_create_new_conversation(self, mock_create_memory):
        """Test creating new conversation"""
        # Setup existing conversations
        self.mock_session_state["conversations"] = {
            "conversation 1": {"thread_id": "thread-1"}
        }
        
        # Mock dependencies  
        mock_memory = Mock()
        mock_create_memory.return_value = mock_memory
        
        mock_manager = Mock()
        mock_manager.create_conversation.return_value = "new-thread-id"
        self.mock_session_state["langgraph_manager"] = mock_manager
        
        new_name = create_new_conversation()
        
        assert new_name == "conversation 2"
        assert new_name in self.mock_session_state["conversations"]
        
        new_conversation = self.mock_session_state["conversations"][new_name]
        assert new_conversation["thread_id"] == "new-thread-id"
        assert new_conversation["title"] == "Conversation 2"
        assert new_conversation["messages"] == []
        assert new_conversation["welcome_shown"] is False
        assert new_conversation["memory_manager"] == mock_memory
        
        # Verify it's set as current
        assert self.mock_session_state["current_conversation"] == new_name
        
        # Verify LangGraph calls
        mock_manager.create_conversation.assert_called_once_with("Conversation 2")
        mock_manager.set_current_thread.assert_called_once_with("new-thread-id")
    
    def test_clear_conversation_memory(self):
        """Test clearing conversation memory"""
        # Setup conversation
        mock_memory = Mock()
        self.mock_session_state["current_conversation"] = "conversation 1" 
        self.mock_session_state["conversations"] = {
            "conversation 1": {
                "thread_id": "thread-1",
                "messages": [{"role": "user", "content": "Hello"}],
                "welcome_shown": True,
                "memory_manager": mock_memory
            }
        }
        
        mock_manager = Mock()
        mock_manager.current_thread_id = "thread-1"
        self.mock_session_state["langgraph_manager"] = mock_manager
        
        clear_conversation_memory()
        
        conversation = self.mock_session_state["conversations"]["conversation 1"]
        assert conversation["messages"] == []
        assert conversation["welcome_shown"] is False
        
        mock_memory.clear.assert_called_once()
        mock_manager.set_current_thread.assert_called_once_with("thread-1") 
        mock_manager.clear.assert_called_once()
    
    def test_should_show_welcome_message(self):
        """Test welcome message display logic"""
        self.mock_session_state["current_conversation"] = "conversation 1"
        self.mock_session_state["conversations"] = {
            "conversation 1": {
                "messages": [],
                "welcome_shown": False
            }
        }
        
        # Should show welcome for empty conversation
        assert should_show_welcome_message() is True
        
        # Should not show if messages exist
        self.mock_session_state["conversations"]["conversation 1"]["messages"] = [
            {"role": "user", "content": "Hello"}
        ]
        assert should_show_welcome_message() is False
        
        # Should not show if already shown
        self.mock_session_state["conversations"]["conversation 1"]["messages"] = []
        self.mock_session_state["conversations"]["conversation 1"]["welcome_shown"] = True
        assert should_show_welcome_message() is False
    
    def test_pending_prompt_management(self):
        """Test pending prompt management"""
        self.mock_session_state["pending_prompt"] = None
        
        # Test setting pending prompt
        set_pending_prompt("Test prompt")
        assert self.mock_session_state["pending_prompt"] == "Test prompt"
        
        # Test getting and clearing pending prompt
        prompt = get_pending_prompt()
        assert prompt == "Test prompt"
        assert self.mock_session_state["pending_prompt"] is None
        
        # Test getting when no prompt pending
        prompt = get_pending_prompt()
        assert prompt is None
    
    @patch('services.chat_service.conversation_manager.st.rerun')
    def test_process_templated_prompt(self, mock_rerun):
        """Test processing templated prompt"""
        self.mock_session_state["current_conversation"] = "conversation 1"
        self.mock_session_state["conversations"] = {
            "conversation 1": {"welcome_shown": False}
        }
        self.mock_session_state["pending_prompt"] = None
        
        process_templated_prompt("Test templated prompt")
        
        # Should mark welcome as shown
        assert self.mock_session_state["conversations"]["conversation 1"]["welcome_shown"] is True
        
        # Should set pending prompt
        assert self.mock_session_state["pending_prompt"] == "Test templated prompt"
        
        # Should trigger rerun
        mock_rerun.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])