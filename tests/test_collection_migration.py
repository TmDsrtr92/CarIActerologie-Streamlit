"""
Tests for collection name migration from legacy format
"""

import pytest
from unittest.mock import Mock, patch
from services.ui_service.chat_interface import ChatInterface
from infrastructure.config.settings import get_config


class TestCollectionMigration:
    """Test collection name migration functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.config = get_config()
        self.chat_interface = ChatInterface()
    
    def test_legacy_collection_name_migration(self):
        """Test that legacy collection names are properly migrated"""
        # Mock session state with legacy value
        mock_session_state = Mock()
        mock_session_state.__contains__ = Mock(return_value=True)
        mock_session_state.selected_collection = "Sub-chapters (Semantic)"
        
        with patch('streamlit.session_state', mock_session_state):
            result = self.chat_interface.get_selected_collection()
            
            # Should migrate to new format
            assert result == "subchapters"
            
            # Should update session state
            assert mock_session_state.selected_collection == "subchapters"
    
    def test_legacy_original_collection_migration(self):
        """Test migration of original collection name"""
        mock_session_state = Mock()
        mock_session_state.__contains__ = Mock(return_value=True)
        mock_session_state.selected_collection = "Original (Character-based)"
        
        with patch('streamlit.session_state', mock_session_state):
            result = self.chat_interface.get_selected_collection()
            
            # Should migrate to new format
            assert result == "original"
            assert mock_session_state.selected_collection == "original"
    
    def test_valid_collection_name_unchanged(self):
        """Test that valid collection names are unchanged"""
        mock_session_state = Mock()
        mock_session_state.__contains__ = Mock(return_value=True)
        mock_session_state.selected_collection = "subchapters"
        
        with patch('streamlit.session_state', mock_session_state):
            result = self.chat_interface.get_selected_collection()
            
            # Should remain unchanged
            assert result == "subchapters"
            assert mock_session_state.selected_collection == "subchapters"
    
    def test_invalid_collection_fallback(self):
        """Test that invalid collection names fall back to default"""
        mock_session_state = Mock()
        mock_session_state.__contains__ = Mock(return_value=True)
        mock_session_state.selected_collection = "invalid_collection"
        
        with patch('streamlit.session_state', mock_session_state):
            result = self.chat_interface.get_selected_collection()
            
            # Should fallback to default
            assert result == self.config.vectorstore.default_collection_key
            assert mock_session_state.selected_collection == self.config.vectorstore.default_collection_key
    
    def test_no_session_state_uses_default(self):
        """Test that missing session state uses default"""
        mock_session_state = Mock()
        mock_session_state.__contains__ = Mock(return_value=False)
        
        with patch('streamlit.session_state', mock_session_state):
            result = self.chat_interface.get_selected_collection()
            
            # Should use default
            assert result == self.config.vectorstore.default_collection_key
    
    def test_collection_options_list_integrity(self):
        """Test that collection options list matches config"""
        collections = list(self.config.vectorstore.collections.keys())
        
        # Should contain expected collections
        assert "subchapters" in collections
        assert "original" in collections
        
        # Should not contain legacy format names
        assert "Sub-chapters (Semantic)" not in collections
        assert "Original (Character-based)" not in collections
    
    @patch('streamlit.session_state')
    def test_collection_index_error_prevention(self, mock_session_state):
        """Test that the fix prevents the original ValueError"""
        # This recreates the original error condition
        mock_session_state.__contains__ = Mock(return_value=True)
        mock_session_state.selected_collection = "Sub-chapters (Semantic)"
        
        collections = list(self.config.vectorstore.collections.keys())
        
        # Before fix, this would raise: ValueError: 'Sub-chapters (Semantic)' is not in list
        # After fix, it should migrate gracefully
        try:
            result = self.chat_interface.get_selected_collection()
            migrated_value = mock_session_state.selected_collection
            
            # Should successfully migrate and be in the valid options
            assert migrated_value in collections
            assert result in collections
            
        except ValueError as e:
            pytest.fail(f"Migration failed, still getting ValueError: {e}")


if __name__ == "__main__":
    pytest.main([__file__])