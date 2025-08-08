"""
Tests for microservices architecture
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

# Test AI Service
from services.ai_service.llm_client import LLMClient, VectorStoreClient, get_llm_client
from services.ai_service.qa_engine import QAEngine, get_qa_engine
from services.ai_service.models import AIResponse, QARequest, RAGState

# Test Auth Service
from services.auth_service.auth_manager import AuthManager, get_auth_manager
from services.auth_service.user_repository import UserRepository, get_user_repository
from services.auth_service.models import User, UserSession

# Test Chat Service
from services.chat_service.conversation_manager import ConversationManager, get_conversation_manager
from services.chat_service.memory_repository import MemoryRepository, get_memory_repository
from services.chat_service.models import Message, Conversation, ConversationSummary

# Test UI Service
from services.ui_service.chat_interface import ChatInterface, get_chat_interface

# Test Infrastructure
from infrastructure.config.settings import get_config
from infrastructure.monitoring.logging_service import get_logger


class TestAIService:
    """Test AI service components"""
    
    def test_llm_client_singleton(self):
        """Test LLM client singleton pattern"""
        client1 = get_llm_client()
        client2 = get_llm_client()
        assert client1 is client2
        assert isinstance(client1, LLMClient)
    
    def test_qa_engine_singleton(self):
        """Test QA engine singleton pattern"""
        engine1 = get_qa_engine()
        engine2 = get_qa_engine()
        assert engine1 is engine2
        assert isinstance(engine1, QAEngine)
    
    def test_ai_response_model(self):
        """Test AI response data model"""
        response = AIResponse(
            answer="Test answer",
            processing_time=1.5
        )
        assert response.answer == "Test answer"
        assert response.processing_time == 1.5
        assert response.context_documents == []
        assert response.metadata == {}
    
    def test_qa_request_model(self):
        """Test QA request data model"""
        request = QARequest(
            question="What is characterology?",
            collection_key="subchapters"
        )
        assert request.question == "What is characterology?"
        assert request.collection_key == "subchapters"
        assert request.chat_history == []


class TestAuthService:
    """Test authentication service components"""
    
    def test_auth_manager_singleton(self):
        """Test auth manager singleton pattern"""
        manager1 = get_auth_manager()
        manager2 = get_auth_manager()
        assert manager1 is manager2
        assert isinstance(manager1, AuthManager)
    
    def test_user_repository_singleton(self):
        """Test user repository singleton pattern"""
        repo1 = get_user_repository()
        repo2 = get_user_repository()
        assert repo1 is repo2
        assert isinstance(repo1, UserRepository)
    
    def test_user_model(self):
        """Test user data model"""
        user = User(
            user_id="test-123",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            role="user"
        )
        assert user.user_id == "test-123"
        assert user.username == "testuser"
        assert user.role == "user"
        assert user.is_active is True
    
    def test_user_session_model(self):
        """Test user session data model"""
        now = datetime.now()
        session = UserSession(
            session_id="session-123",
            user_id="user-123",
            username="testuser",
            role="user",
            created_at=now,
            expires_at=now,
            last_activity=now
        )
        assert session.session_id == "session-123"
        assert session.user_id == "user-123"
        assert session.remember_me is False


class TestChatService:
    """Test chat service components"""
    
    def test_conversation_manager_singleton(self):
        """Test conversation manager singleton pattern"""
        manager1 = get_conversation_manager()
        manager2 = get_conversation_manager()
        assert manager1 is manager2
        assert isinstance(manager1, ConversationManager)
    
    def test_memory_repository_singleton(self):
        """Test memory repository singleton pattern"""
        repo1 = get_memory_repository()
        repo2 = get_memory_repository()
        assert repo1 is repo2
        assert isinstance(repo1, MemoryRepository)
    
    def test_message_model(self):
        """Test message data model"""
        message = Message(
            role="user",
            content="Hello, world!"
        )
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert isinstance(message.created_at, datetime)
        assert message.metadata == {}
    
    def test_conversation_model(self):
        """Test conversation data model"""
        conversation = Conversation(
            conversation_id="conv-123",
            thread_id="thread-123",
            title="Test Conversation"
        )
        assert conversation.conversation_id == "conv-123"
        assert conversation.thread_id == "thread-123"
        assert conversation.title == "Test Conversation"
        assert conversation.messages == []
        assert conversation.is_active is True


class TestUIService:
    """Test UI service components"""
    
    def test_chat_interface_singleton(self):
        """Test chat interface singleton pattern"""
        interface1 = get_chat_interface()
        interface2 = get_chat_interface()
        assert interface1 is interface2
        assert isinstance(interface1, ChatInterface)


class TestInfrastructure:
    """Test infrastructure components"""
    
    def test_config_singleton(self):
        """Test configuration singleton pattern"""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2
    
    def test_logger_availability(self):
        """Test logger is available"""
        logger = get_logger("test_module")
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')


class TestServiceIntegration:
    """Test service integration and compatibility"""
    
    @patch('streamlit.session_state')
    def test_conversation_manager_initialization(self, mock_session_state):
        """Test conversation manager can initialize properly"""
        mock_session_state.__contains__ = Mock(return_value=False)
        mock_session_state.get = Mock(return_value=None)
        
        manager = get_conversation_manager()
        
        # Test basic functionality without actual session state
        assert hasattr(manager, 'initialize_conversations')
        assert hasattr(manager, 'get_current_conversation')
        assert hasattr(manager, 'create_new_conversation')
    
    def test_service_dependencies(self):
        """Test that services can be instantiated with their dependencies"""
        # Test AI service dependencies
        qa_engine = get_qa_engine()
        assert qa_engine is not None
        
        # Test chat service dependencies
        conv_manager = get_conversation_manager()
        assert conv_manager is not None
        
        # Test auth service dependencies
        auth_manager = get_auth_manager()
        assert auth_manager is not None
        
        # Test UI service dependencies
        chat_interface = get_chat_interface()
        assert chat_interface is not None
    
    def test_legacy_compatibility(self):
        """Test that legacy imports still work"""
        # Test legacy conversation manager imports
        from services.chat_service.conversation_manager import (
            initialize_conversations,
            get_current_conversation,
            get_conversation_names
        )
        
        assert callable(initialize_conversations)
        assert callable(get_current_conversation)
        assert callable(get_conversation_names)
        
        # Test legacy UI service imports
        from services.ui_service.chat_interface import (
            get_langfuse_handler,
            create_stream_handler,
            render_conversation_sidebar
        )
        
        assert callable(get_langfuse_handler)
        assert callable(create_stream_handler)
        assert callable(render_conversation_sidebar)


if __name__ == "__main__":
    pytest.main([__file__])