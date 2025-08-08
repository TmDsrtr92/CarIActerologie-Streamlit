"""
Authentication service - handles user authentication and authorization.
Refactored from auth/streamlit_auth.py into a service-oriented architecture.
"""

import streamlit as st
from typing import Optional, Callable
import time
import json
import base64
from datetime import datetime, timedelta

from services.auth_service.user_repository import get_user_repository
from services.auth_service.models import User, UserSession
from infrastructure.monitoring.logging_service import get_logger
from infrastructure.config.settings import get_config, is_streamlit_cloud


class AuthManager:
    """
    Main authentication manager service.
    Handles user authentication, session management, and authorization.
    """
    
    def __init__(self):
        self.user_repository = get_user_repository()
        self.logger = get_logger(__name__)
        self.config = get_config()
        self.cookie_name = "streamlit_session_id"
        self.is_cloud = is_streamlit_cloud()
    
    def require_authentication(self, page_func: Callable):
        """
        Decorator to require authentication for a page
        
        Args:
            page_func: Function to call if authenticated
        """
        # Check if authentication is disabled (for development)
        if not self.config.auth.enabled:
            return page_func()
        
        # Auto-login as guest in cloud environment
        if self.is_cloud and not self.get_current_session():
            self._auto_login_guest()
        
        # Check for existing session
        current_session = self.get_current_session()
        
        if current_session:
            # User is authenticated, call the page function
            return page_func()
        else:
            # Show login form (local environment only)
            return self.render_login_form()
    
    def get_current_session(self) -> Optional[UserSession]:
        """
        Get current user session from Streamlit session state or stored session
        
        Returns:
            UserSession if valid, None otherwise
        """
        # Check if session exists in session state
        if "user_session" not in st.session_state:
            # Try to restore from stored session (localStorage)
            stored_session_id = self._get_stored_session()
            if stored_session_id:
                # Validate the stored session with the repository
                session = self.user_repository.validate_session(stored_session_id)
                if session:
                    # Restore session to session state
                    st.session_state.user_session = {
                        "session_id": session.session_id,
                        "user_id": session.user_id,
                        "username": session.username,
                        "role": session.role,
                        "last_activity": session.last_activity.isoformat()
                    }
                    self.logger.info(f"Session restored from storage for user: {session.username}")
                    return session
                else:
                    # Stored session is invalid, clear it
                    self._clear_stored_session()
            
            return None
        
        session_data = st.session_state.user_session
        session_id = session_data.get("session_id")
        if not session_id:
            return None
        
        # Handle guest sessions (don't validate through repository)
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
        
        # Validate regular user session with repository
        session = self.user_repository.validate_session(session_id)
        
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
        
        return self.user_repository.get_user_by_id(session.user_id)
    
    def login(self, username: str, password: str, remember_me: bool = False) -> bool:
        """
        Authenticate user and create session
        
        Args:
            username: Username or email
            password: Password
            remember_me: If True, create extended session (30 days)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            user = self.user_repository.authenticate(username, password)
            
            if not user:
                return False
            
            # Create session with remember me option
            session = self.user_repository.create_session(user, remember_me)
            
            # Store session in Streamlit session state
            st.session_state.user_session = {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "username": session.username,
                "role": session.role,
                "last_activity": session.last_activity.isoformat()
            }
            
            # Store session locally for persistence if remember me is enabled
            if remember_me:
                self._store_session_locally(session.session_id, remember_me)
            
            self.logger.info(f"User logged in: {username} (remember_me: {remember_me})")
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
                    self.user_repository.logout(session_id)
                
                self.clear_session()
            
            # Clear stored session from browser localStorage
            self._clear_stored_session()
            
            self.logger.info("User logged out")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during logout: {e}")
            return False
    
    def _auto_login_guest(self):
        """Auto-login as guest user for cloud environment"""
        try:
            # Attempt to login with default guest credentials
            success = self.login("guest", "guest123")
            if success:
                self.logger.info("Auto-logged in as guest user for cloud environment")
            else:
                self.logger.warning("Failed to auto-login as guest user")
        except Exception as e:
            self.logger.error(f"Error during guest auto-login: {e}")
    
    def clear_session(self):
        """Clear session data from Streamlit session state"""
        # Get user ID before clearing session
        user_id = None
        if "user_session" in st.session_state:
            user_session = st.session_state.user_session
            if isinstance(user_session, dict):
                user_id = user_session.get("user_id")
        
        # Always clear these keys
        generic_keys_to_clear = ["user_session", "pending_prompt"]
        
        # Clear user-specific keys if we have a user ID
        user_specific_keys = []
        if user_id:
            user_specific_keys = [
                f"conversations_{user_id}",
                f"current_conversation_{user_id}",
                f"langgraph_manager_{user_id}"
            ]
        
        # Also clear generic fallback keys (for guests or old sessions)
        fallback_keys = ["conversations", "current_conversation", "langgraph_manager"]
        
        all_keys = generic_keys_to_clear + user_specific_keys + fallback_keys
        
        for key in all_keys:
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
            user = self.user_repository.create_user(
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
                    # Enhanced authentication loading with progress
                    progress_placeholder = st.empty()
                    with progress_placeholder.container():
                        auth_status = st.status("🔐 Authenticating...", expanded=True)
                        with auth_status:
                            st.write("🔍 Verifying credentials...")
                            time.sleep(0.5)  # Brief visual feedback
                            
                            if self.login(username, password, False):  # Always False for remember_me
                                st.write("✅ Credentials validated")
                                st.write("🚀 Setting up your session...")
                                auth_status.update(label="✅ Login successful!", state="complete")
                                time.sleep(1)  # Brief pause for user feedback
                                progress_placeholder.empty()
                                st.success("Welcome back! Redirecting...")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.write("❌ Invalid credentials")
                                auth_status.update(label="❌ Authentication failed", state="error")
                                time.sleep(1)
                                progress_placeholder.empty()
                                st.error("❌ Invalid username or password")
            
            if forgot_password:
                self._show_password_reset_form()

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
                    # Enhanced registration loading with progress
                    reg_progress = st.empty()
                    with reg_progress.container():
                        reg_status = st.status("🆕 Creating your account...", expanded=True)
                        with reg_status:
                            st.write("🔍 Validating information...")
                            time.sleep(0.3)
                            st.write("🔐 Securing your password...")
                            time.sleep(0.3)
                            st.write("💾 Creating user profile...")
                            
                            success, message = self.register_user(
                                username, email, full_name, password, confirm_password
                            )
                            
                            if success:
                                st.write("✅ Account created successfully!")
                                reg_status.update(label="✅ Registration complete!", state="complete")
                                time.sleep(1)
                                reg_progress.empty()
                                st.success(f"✅ {message}")
                                st.info("Please switch to the Login tab to sign in with your new account.")
                            else:
                                st.write(f"❌ {message}")
                                reg_status.update(label="❌ Registration failed", state="error")
                                time.sleep(1)
                                reg_progress.empty()
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

    def _show_password_reset_form(self):
        """Show password reset request form"""
        st.subheader("🔑 Password Reset")
        
        # Check if we're handling a reset token from URL
        query_params = st.query_params
        if "reset_token" in query_params:
            self._handle_password_reset(query_params["reset_token"])
            return
        
        with st.form("password_reset_form"):
            st.write("Enter your email address to receive a password reset link:")
            
            email = st.text_input("📧 Email Address", placeholder="your@email.com")
            submit_reset = st.form_submit_button("🔑 Send Reset Link", type="primary", use_container_width=True)
            
            if submit_reset:
                if not email:
                    st.error("Please enter your email address")
                elif "@" not in email:
                    st.error("Please enter a valid email address")
                else:
                    self._send_password_reset_email(email)

    def _send_password_reset_email(self, email: str):
        """Send password reset email (mock implementation)"""
        reset_progress = st.empty()
        
        with reset_progress.container():
            reset_status = st.status("📧 Sending reset link...", expanded=True)
            with reset_status:
                st.write("🔍 Checking email address...")
                time.sleep(0.5)
                
                # Create reset token
                token = self.user_repository.create_password_reset_token(email)
                
                if token:
                    st.write("✅ Email found in system")
                    st.write("📧 Generating reset link...")
                    time.sleep(0.5)
                    
                    # Generate reset URL
                    base_url = st.get_option("server.baseUrlPath") or "http://localhost:8501"
                    reset_url = f"{base_url}?reset_token={token}"
                    
                    st.write("🚀 Sending email...")
                    time.sleep(0.5)
                    
                    reset_status.update(label="✅ Reset link sent!", state="complete")
                    
                    # Since we don't have email configured, show the link directly
                    st.success("✅ Password reset link generated!")
                    st.info("📧 **For demo purposes, here's your reset link:**")
                    st.code(reset_url, language="text")
                    
                    st.warning("⚠️ **Note:** In production, this link would be sent to your email address. The link expires in 1 hour.")
                    
                else:
                    st.write("❌ Email not found")
                    reset_status.update(label="❌ Email not found", state="error")
                    time.sleep(1)
                    reset_progress.empty()
                    st.error("❌ No account found with that email address")

    def _handle_password_reset(self, token: str):
        """Handle password reset with token"""
        st.subheader("🔐 Reset Your Password")
        
        # Clear the token from URL
        st.query_params.clear()
        
        # Validate token
        user_id = self.user_repository.validate_reset_token(token)
        if not user_id:
            st.error("❌ Invalid or expired reset link")
            st.info("Please request a new password reset link.")
            return
        
        with st.form("new_password_form"):
            st.success("✅ Valid reset link! Enter your new password:")
            
            new_password = st.text_input("🔒 New Password", type="password", placeholder="Enter new password")
            confirm_password = st.text_input("🔒 Confirm Password", type="password", placeholder="Confirm new password")
            
            reset_password = st.form_submit_button("🔐 Reset Password", type="primary", use_container_width=True)
            
            if reset_password:
                if not new_password or not confirm_password:
                    st.error("Please enter both password fields")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters")
                else:
                    reset_progress = st.empty()
                    with reset_progress.container():
                        reset_status = st.status("🔐 Resetting password...", expanded=True)
                        with reset_status:
                            st.write("🔒 Updating password...")
                            time.sleep(0.5)
                            
                            if self.user_repository.reset_password_with_token(token, new_password):
                                st.write("✅ Password updated successfully!")
                                reset_status.update(label="✅ Password reset complete!", state="complete")
                                time.sleep(1)
                                reset_progress.empty()
                                st.success("✅ Password has been reset successfully!")
                                st.info("You can now log in with your new password.")
                            else:
                                st.write("❌ Failed to reset password")
                                reset_status.update(label="❌ Reset failed", state="error")
                                time.sleep(1)
                                reset_progress.empty()
                                st.error("❌ Failed to reset password. Please try again.")

    def _store_session_locally(self, session_id: str, remember_me: bool = False):
        """Store session ID in browser localStorage"""
        try:
            # Calculate expiration timestamp
            from datetime import datetime, timedelta
            if remember_me:
                expires = datetime.now() + timedelta(days=30)
            else:
                expires = datetime.now() + timedelta(hours=24)
            
            expires_timestamp = int(expires.timestamp() * 1000)  # JavaScript uses milliseconds
            
            storage_script = f"""
            <script>
                try {{
                    const sessionData = {{
                        sessionId: "{session_id}",
                        expiresAt: {expires_timestamp},
                        rememberMe: {str(remember_me).lower()}
                    }};
                    localStorage.setItem("{self.cookie_name}", JSON.stringify(sessionData));
                    console.log("Session stored locally with expiration:", new Date({expires_timestamp}));
                }} catch (e) {{
                    console.error("Failed to store session locally:", e);
                }}
            </script>
            """
            st.components.v1.html(storage_script, height=0)
            self.logger.debug(f"Session stored locally for session {session_id[:8]}...")
            
        except Exception as e:
            self.logger.error(f"Failed to store session locally: {e}")

    def _get_stored_session(self) -> Optional[str]:
        """Get session ID from browser localStorage"""
        try:
            # Use a unique key to store/retrieve session data
            storage_key = f"stored_session_{hash(st.get_option('server.address') or 'localhost')}"
            
            if storage_key not in st.session_state:
                # Create a component to read from localStorage
                retrieval_script = f"""
                <script>
                    try {{
                        const storedData = localStorage.getItem("{self.cookie_name}");
                        if (storedData) {{
                            const sessionData = JSON.parse(storedData);
                            const now = Date.now();
                            
                            if (sessionData.expiresAt && now < sessionData.expiresAt) {{
                                // Session is still valid
                                console.log("Valid session found in localStorage");
                                
                                // Try URL-based communication instead
                                const url = new URL(window.location);
                                url.searchParams.set('session_restore', sessionData.sessionId);
                                if (window.location.href !== url.href) {{
                                    window.location.href = url.href;
                                }}
                            }} else {{
                                console.log("Stored session expired, clearing...");
                                localStorage.removeItem("{self.cookie_name}");
                            }}
                        }}
                    }} catch (e) {{
                        console.error("Failed to retrieve stored session:", e);
                    }}
                </script>
                """
                st.components.v1.html(retrieval_script, height=0)
                st.session_state[storage_key] = True
            
            # Check URL parameters for session restoration
            query_params = st.query_params
            if "session_restore" in query_params:
                session_id = query_params["session_restore"]
                # Clear the parameter to clean up URL
                st.query_params.clear()
                return session_id
                
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get stored session: {e}")
            return None

    def _clear_stored_session(self):
        """Clear stored session from browser localStorage"""
        try:
            clear_script = f"""
            <script>
                try {{
                    localStorage.removeItem("{self.cookie_name}");
                    console.log("Stored session cleared");
                }} catch (e) {{
                    console.error("Failed to clear stored session:", e);
                }}
            </script>
            """
            st.components.v1.html(clear_script, height=0)
            self.logger.debug("Stored session cleared")
            
        except Exception as e:
            self.logger.error(f"Failed to clear stored session: {e}")

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


# Global authentication service instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get the global authentication manager service instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


def require_auth(page_func: Callable):
    """
    Decorator to require authentication for a page
    
    Usage:
        @require_auth
        def my_protected_page():
            st.write("This page requires authentication")
    """
    auth = get_auth_manager()
    return auth.require_authentication(page_func)