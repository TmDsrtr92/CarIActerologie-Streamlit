"""
Streamlit authentication components and session management
"""

import streamlit as st
from typing import Optional, Callable
import time
from datetime import datetime, timedelta

from auth.user_manager import get_user_manager, User, UserSession
from utils.logging_config import get_logger
from config.app_config import get_config


class StreamlitAuth:
    """
    Streamlit authentication handler
    """
    
    def __init__(self):
        self.user_manager = get_user_manager()
        self.logger = get_logger(__name__)
        self.config = get_config()
    
    def require_authentication(self, page_func: Callable):
        """
        Decorator to require authentication for a page
        
        Args:
            page_func: Function to call if authenticated
        """
        # Check if authentication is disabled (for development)
        if not self.config.auth.enabled:
            return page_func()
        
        # Check for existing session
        current_session = self.get_current_session()
        
        if current_session:
            # User is authenticated, call the page function
            return page_func()
        else:
            # Show login form
            return self.render_login_form()
    
    def get_current_session(self) -> Optional[UserSession]:
        """
        Get current user session from Streamlit session state
        
        Returns:
            UserSession if valid, None otherwise
        """
        # Check if session exists in session state
        if "user_session" not in st.session_state:
            return None
        
        session_data = st.session_state.user_session
        session_id = session_data.get("session_id")
        if not session_id:
            return None
        
        # Handle guest sessions (don't validate through user manager)
        if session_data.get("role") == "guest":
            # Guest sessions are valid as long as they exist in session state
            return UserSession(
                session_id=session_data["session_id"],
                user_id=session_data["user_id"],
                username=session_data["username"],
                role=session_data["role"],
                created_at=datetime.fromisoformat(session_data["last_activity"]),
                expires_at=datetime.now() + timedelta(hours=24),  # Guest sessions expire after 24h
                last_activity=datetime.fromisoformat(session_data["last_activity"])
            )
        
        # Validate regular user session with user manager
        session = self.user_manager.validate_session(session_id)
        
        if not session:
            # Session is invalid, clear from session state
            self.clear_session()
            return None
        
        # Update session state with current session info
        st.session_state.user_session = {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "username": session.username,
            "role": session.role,
            "last_activity": session.last_activity.isoformat()
        }
        
        return session
    
    def get_current_user(self) -> Optional[User]:
        """
        Get current user from session
        
        Returns:
            User object if authenticated, None otherwise
        """
        session = self.get_current_session()
        if not session:
            return None
        
        # Handle guest sessions (create a temporary User object)
        if session.role == "guest":
            return User(
                user_id=session.user_id,
                username=session.username,
                email="guest@example.com",
                full_name=session.username,
                role="guest",
                created_at=session.created_at,
                last_login=session.last_activity,
                is_active=True
            )
        
        return self.user_manager.get_user_by_id(session.user_id)
    
    def login(self, username: str, password: str) -> bool:
        """
        Authenticate user and create session
        
        Args:
            username: Username or email
            password: Password
            
        Returns:
            True if successful, False otherwise
        """
        try:
            user = self.user_manager.authenticate(username, password)
            
            if not user:
                return False
            
            # Create session
            session = self.user_manager.create_session(user)
            
            # Store session in Streamlit session state
            st.session_state.user_session = {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "username": session.username,
                "role": session.role,
                "last_activity": session.last_activity.isoformat()
            }
            
            self.logger.info(f"User logged in: {username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during login: {e}")
            return False
    
    def logout(self) -> bool:
        """
        Logout current user
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if "user_session" in st.session_state:
                session_id = st.session_state.user_session.get("session_id")
                if session_id:
                    self.user_manager.logout(session_id)
                
                self.clear_session()
            
            self.logger.info("User logged out")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during logout: {e}")
            return False
    
    def clear_session(self):
        """Clear session data from Streamlit session state"""
        keys_to_clear = [
            "user_session", "conversations", "current_conversation", 
            "langgraph_manager", "pending_prompt"
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def register_user(self, username: str, email: str, full_name: str, 
                     password: str, confirm_password: str) -> tuple[bool, str]:
        """
        Register a new user
        
        Args:
            username: Desired username
            email: Email address
            full_name: Full name
            password: Password
            confirm_password: Password confirmation
            
        Returns:
            (success, message) tuple
        """
        try:
            # Validate input
            if not all([username, email, full_name, password, confirm_password]):
                return False, "All fields are required"
            
            if password != confirm_password:
                return False, "Passwords do not match"
            
            if len(password) < 8:
                return False, "Password must be at least 8 characters"
            
            if "@" not in email:
                return False, "Please enter a valid email address"
            
            # Create user
            user = self.user_manager.create_user(
                username=username,
                email=email,
                full_name=full_name,
                password=password
            )
            
            if user:
                self.logger.info(f"User registered: {username}")
                return True, "Account created successfully! Please log in."
            else:
                return False, "Failed to create account"
                
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            self.logger.error(f"Error during registration: {e}")
            return False, "An error occurred during registration"
    
    def render_login_form(self):
        """Render login/registration form"""
        st.title("🔐 CarIActérologie - Authentication")
        
        # Add logo or branding
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h2>Welcome to CarIActérologie</h2>
            <p>AI-powered Characterology Assistant</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Tabs for login and registration
        login_tab, register_tab = st.tabs(["🔑 Login", "📝 Register"])
        
        with login_tab:
            self._render_login_tab()
        
        with register_tab:
            self._render_register_tab()
        
        # Guest mode option (if enabled)
        if self.config.auth.allow_guest_mode:
            st.divider()
            if st.button("🎭 Continue as Guest", type="secondary"):
                self._create_guest_session()
                st.rerun()
    
    def _render_login_tab(self):
        """Render login form"""
        with st.form("login_form"):
            st.subheader("Sign In")
            
            username = st.text_input("👤 Username or Email", placeholder="Enter your username or email")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                login_clicked = st.form_submit_button("🔑 Sign In", type="primary", use_container_width=True)
            
            with col2:
                forgot_password = st.form_submit_button("❓ Forgot Password", use_container_width=True)
            
            if login_clicked:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    with st.spinner("Authenticating..."):
                        if self.login(username, password):
                            st.success("✅ Login successful!")
                            time.sleep(1)  # Brief pause for user feedback
                            st.rerun()
                        else:
                            st.error("❌ Invalid username or password")
            
            if forgot_password:
                st.info("🔧 Password reset functionality coming soon! Please contact your administrator.")
    
    def _render_register_tab(self):
        """Render registration form"""
        with st.form("register_form"):
            st.subheader("Create Account")
            
            col1, col2 = st.columns(2)
            
            with col1:
                username = st.text_input("👤 Username", placeholder="Choose a username")
                full_name = st.text_input("👨‍💼 Full Name", placeholder="Your full name")
            
            with col2:
                email = st.text_input("📧 Email", placeholder="your@email.com")
                # Future: Add role selection for admin users
            
            password = st.text_input("🔒 Password", type="password", placeholder="Choose a strong password")
            confirm_password = st.text_input("🔒 Confirm Password", type="password", placeholder="Confirm your password")
            
            # Terms acceptance
            terms_accepted = st.checkbox("I agree to the Terms of Service and Privacy Policy")
            
            register_clicked = st.form_submit_button("📝 Create Account", type="primary", use_container_width=True)
            
            if register_clicked:
                if not terms_accepted:
                    st.error("Please accept the Terms of Service to continue")
                else:
                    with st.spinner("Creating account..."):
                        success, message = self.register_user(
                            username, email, full_name, password, confirm_password
                        )
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.info("Please switch to the Login tab to sign in with your new account.")
                        else:
                            st.error(f"❌ {message}")
    
    def _create_guest_session(self):
        """Create a temporary guest session"""
        import uuid
        guest_id = f"guest_{str(uuid.uuid4())[:8]}"
        
        st.session_state.user_session = {
            "session_id": f"guest_session_{guest_id}",
            "user_id": guest_id,
            "username": f"Guest {guest_id[-4:]}",
            "role": "guest",
            "last_activity": datetime.now().isoformat()
        }
        
        self.logger.info(f"Guest session created: {guest_id}")
    
    def render_user_menu(self):
        """Render user menu in sidebar"""
        session = self.get_current_session()
        if not session:
            return
        
        with st.sidebar:
            st.divider()
            st.subheader("👤 User Account")
            
            # User info
            st.write(f"**Welcome, {session.username}!**")
            st.write(f"Role: {session.role.title()}")
            
            # Session info
            with st.expander("Session Info"):
                st.write(f"Session ID: `{session.session_id[:8]}...`")
                st.write(f"Last Activity: {session.last_activity.strftime('%H:%M:%S')}")
                
                # Session expires at
                if hasattr(session, 'expires_at'):
                    st.write(f"Expires: {session.expires_at.strftime('%Y-%m-%d %H:%M')}")
            
            # User actions
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("⚙️ Settings", use_container_width=True):
                    st.session_state.show_user_settings = True
            
            with col2:
                if st.button("🚪 Logout", use_container_width=True):
                    if self.logout():
                        st.success("Logged out successfully!")
                        time.sleep(1)
                        st.rerun()
    
    def render_user_settings(self):
        """Render user settings dialog"""
        if not st.session_state.get("show_user_settings", False):
            return
        
        user = self.get_current_user()
        if not user:
            return
        
        with st.container():
            st.subheader("⚙️ User Settings")
            
            with st.form("user_settings_form"):
                st.write("**Account Information**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    new_full_name = st.text_input("Full Name", value=user.full_name)
                    new_email = st.text_input("Email", value=user.email)
                
                with col2:
                    st.write(f"**Username:** {user.username}")
                    st.write(f"**Role:** {user.role.title()}")
                    st.write(f"**Member Since:** {user.created_at.strftime('%Y-%m-%d')}")
                
                st.divider()
                st.write("**Preferences**")
                
                # Add user preference settings here
                preferred_collection = st.selectbox(
                    "Default Collection",
                    ["Sub-chapters (Semantic)", "Original (Character-based)"],
                    help="Choose your preferred vector store collection"
                )
                
                enable_notifications = st.checkbox("Enable Notifications", value=True)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    save_clicked = st.form_submit_button("💾 Save Changes", type="primary")
                
                with col2:
                    cancel_clicked = st.form_submit_button("❌ Cancel")
                
                with col3:
                    if user.role == "admin":
                        admin_clicked = st.form_submit_button("🔧 Admin Panel")
                
                if save_clicked:
                    st.success("Settings saved successfully!")
                    st.session_state.show_user_settings = False
                    st.rerun()
                
                if cancel_clicked:
                    st.session_state.show_user_settings = False
                    st.rerun()


# Global authentication instance
_streamlit_auth: Optional[StreamlitAuth] = None


def get_auth() -> StreamlitAuth:
    """Get the global Streamlit authentication instance"""
    global _streamlit_auth
    if _streamlit_auth is None:
        _streamlit_auth = StreamlitAuth()
    return _streamlit_auth


def require_auth(page_func: Callable):
    """
    Decorator to require authentication for a page
    
    Usage:
        @require_auth
        def my_protected_page():
            st.write("This page requires authentication")
    """
    auth = get_auth()
    return auth.require_authentication(page_func)