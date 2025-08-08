"""
Simple User Session Management
Replaces the entire authentication system with basic session-only user tracking.
No login, no passwords, no database - just simple user identification for conversations.
"""

import streamlit as st
import uuid
from datetime import datetime
from typing import Dict, Optional

from infrastructure.monitoring.logging_service import get_logger


class SimpleUserSession:
    """
    Simple user session manager that handles basic user info in Streamlit session state.
    No authentication, just user identification for personalization and conversation tracking.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        # Don't initialize here - do it lazily when first accessed
    
    def _ensure_user_session(self):
        """Ensure user session exists in session state"""
        if "user" not in st.session_state:
            # Create a simple user with auto-generated ID
            user_id = str(uuid.uuid4())[:8]  # Short ID
            
            st.session_state.user = {
                "id": user_id,
                "name": f"User {user_id}",  # Default display name
                "created_at": datetime.now().isoformat(),
                "preferences": {
                    "language": "fr"
                }
            }
            
            self.logger.info(f"Created simple user session: {user_id}")
    
    def get_user_id(self) -> str:
        """Get current user ID"""
        self._ensure_user_session()
        return st.session_state.user["id"]
    
    def get_user_name(self) -> str:
        """Get current user display name"""
        self._ensure_user_session()
        return st.session_state.user["name"]
    
    def set_user_name(self, name: str):
        """Set user display name"""
        self._ensure_user_session()
        st.session_state.user["name"] = name
        self.logger.info(f"Updated user name to: {name}")
    
    def get_user_info(self) -> Dict:
        """Get complete user info"""
        self._ensure_user_session()
        return st.session_state.user.copy()
    
    def get_preference(self, key: str, default=None):
        """Get user preference"""
        self._ensure_user_session()
        return st.session_state.user["preferences"].get(key, default)
    
    def set_preference(self, key: str, value):
        """Set user preference"""
        self._ensure_user_session()
        st.session_state.user["preferences"][key] = value
        self.logger.debug(f"Set preference {key} = {value}")
    
    def render_user_info_sidebar(self):
        """Render simple user info in sidebar"""
        with st.sidebar:
            st.divider()
            
            # User info section
            st.markdown("**👤 User Info**")
            
            # Editable user name
            current_name = self.get_user_name()
            new_name = st.text_input("Display Name", value=current_name, key="user_name_input")
            
            if new_name != current_name:
                self.set_user_name(new_name)
                st.rerun()
            
            # Show user ID (read-only)
            st.text(f"ID: {self.get_user_id()}")
    
    def get_user_context_for_conversations(self) -> Dict:
        """Get minimal user context for conversation system"""
        self._ensure_user_session()
        return {
            "user_id": self.get_user_id(),
            "user_name": self.get_user_name()
        }
    
    def clear_session(self):
        """Clear user session (creates new user)"""
        if "user" in st.session_state:
            del st.session_state.user
        self._ensure_user_session()
        self.logger.info("User session cleared and recreated")


# Global instance
_simple_user_session: Optional[SimpleUserSession] = None


def get_simple_user_session() -> SimpleUserSession:
    """Get global simple user session instance"""
    global _simple_user_session
    if _simple_user_session is None:
        _simple_user_session = SimpleUserSession()
    return _simple_user_session


# Convenience functions for backward compatibility
def get_current_user_id() -> str:
    """Get current user ID - replacement for auth system"""
    return get_simple_user_session().get_user_id()


def get_current_user_name() -> str:
    """Get current user name - replacement for auth system"""
    return get_simple_user_session().get_user_name()


def get_user_context() -> Dict:
    """Get user context for conversations - replacement for auth system"""
    return get_simple_user_session().get_user_context_for_conversations()