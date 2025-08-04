"""
User management system for multi-user authentication
"""

import hashlib
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import streamlit as st
import bcrypt

from config.app_config import get_config
from utils.logging_config import get_logger


@dataclass
class User:
    """User data model"""
    user_id: str
    username: str
    email: str
    full_name: str
    role: str = "user"  # user, admin, moderator
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    is_active: bool = True
    preferences: Dict = field(default_factory=dict)


@dataclass
class UserSession:
    """User session data model"""
    session_id: str
    user_id: str
    username: str
    role: str
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    remember_me: bool = False


class UserManager:
    """
    Manages user authentication, registration, and session handling
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize user manager
        
        Args:
            db_path: Path to user database (defaults to config setting)
        """
        self.logger = get_logger(__name__)
        config = get_config()
        self.db_path = db_path or "users.db"
        self.session_timeout_hours = 24  # Session expires after 24 hours
        
        self._init_database()
    
    def _init_database(self):
        """Initialize user database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TEXT NOT NULL,
                last_login TEXT,
                is_active BOOLEAN DEFAULT 1,
                preferences TEXT DEFAULT '{}'
            )
        """)
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                remember_me BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # User preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, preference_key),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_conversations (
                conversation_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                welcome_shown BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Conversation messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES user_conversations (conversation_id)
            )
        """)
        
        conn.commit()
        
        # Run database migrations
        self._run_migrations(cursor)
        
        conn.commit()
        conn.close()
        
        self.logger.info("User database initialized")
    
    def _run_migrations(self, cursor):
        """Run database schema migrations"""
        try:
            # Check if remember_me column exists in user_sessions table
            cursor.execute("PRAGMA table_info(user_sessions)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'remember_me' not in columns:
                self.logger.info("Adding remember_me column to user_sessions table")
                cursor.execute("ALTER TABLE user_sessions ADD COLUMN remember_me BOOLEAN DEFAULT 0")
                self.logger.info("Migration completed: remember_me column added")
        
        except Exception as e:
            self.logger.error(f"Error during migration: {e}")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_user(self, username: str, email: str, full_name: str, 
                   password: str, role: str = "user") -> Optional[User]:
        """
        Create a new user account
        
        Args:
            username: Unique username
            email: User email address
            full_name: User's full name
            password: Plain text password (will be hashed)
            role: User role (user, admin, moderator)
            
        Returns:
            User object if successful, None if failed
        """
        try:
            # Validate input
            if not all([username, email, full_name, password]):
                raise ValueError("All fields are required")
            
            if len(password) < 8:
                raise ValueError("Password must be at least 8 characters")
            
            # Generate user ID
            user_id = str(uuid.uuid4())
            password_hash = self._hash_password(password)
            created_at = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO users (user_id, username, email, full_name, 
                                 password_hash, role, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, email, full_name, password_hash, 
                  role, created_at, True))
            
            conn.commit()
            conn.close()
            
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                full_name=full_name,
                role=role,
                created_at=datetime.fromisoformat(created_at)
            )
            
            self.logger.info(f"User created successfully: {username}")
            return user
            
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                self.logger.warning(f"Username already exists: {username}")
                raise ValueError("Username already exists")
            elif "email" in str(e):
                self.logger.warning(f"Email already exists: {email}")
                raise ValueError("Email already exists")
            else:
                self.logger.error(f"Database integrity error: {e}")
                raise ValueError("Failed to create user")
        
        except Exception as e:
            self.logger.error(f"Error creating user: {e}")
            return None
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username and password
        
        Args:
            username: Username or email
            password: Plain text password
            
        Returns:
            User object if authentication successful, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Try username first, then email
            cursor.execute("""
                SELECT user_id, username, email, full_name, password_hash, 
                       role, created_at, last_login, is_active, preferences
                FROM users 
                WHERE (username = ? OR email = ?) AND is_active = 1
            """, (username, username))
            
            row = cursor.fetchone()
            
            if not row:
                self.logger.warning(f"User not found: {username}")
                return None
            
            # Verify password
            if not self._verify_password(password, row[4]):
                self.logger.warning(f"Invalid password for user: {username}")
                return None
            
            # Update last login
            user_id = row[0]
            now = datetime.now().isoformat()
            cursor.execute("""
                UPDATE users SET last_login = ? WHERE user_id = ?
            """, (now, user_id))
            
            conn.commit()
            conn.close()
            
            user = User(
                user_id=row[0],
                username=row[1],
                email=row[2],
                full_name=row[3],
                role=row[5],
                created_at=datetime.fromisoformat(row[6]),
                last_login=datetime.fromisoformat(now),
                is_active=bool(row[8])
            )
            
            self.logger.info(f"User authenticated successfully: {username}")
            return user
            
        except Exception as e:
            self.logger.error(f"Error authenticating user: {e}")
            return None
    
    def create_session(self, user: User, remember_me: bool = False) -> UserSession:
        """
        Create a new user session
        
        Args:
            user: Authenticated user
            remember_me: If True, create extended session (30 days vs 24 hours)
            
        Returns:
            UserSession object
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Extended session for remember me (30 days vs 24 hours)
        if remember_me:
            expires_at = now + timedelta(days=30)
        else:
            expires_at = now + timedelta(hours=self.session_timeout_hours)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_sessions (session_id, user_id, created_at, 
                                         expires_at, last_activity, is_active, remember_me)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, user.user_id, now.isoformat(), 
                  expires_at.isoformat(), now.isoformat(), True, remember_me))
            
            conn.commit()
            conn.close()
            
            session = UserSession(
                session_id=session_id,
                user_id=user.user_id,
                username=user.username,
                role=user.role,
                created_at=now,
                expires_at=expires_at,
                last_activity=now,
                remember_me=remember_me
            )
            
            self.logger.info(f"Session created for user: {user.username}")
            return session
            
        except Exception as e:
            self.logger.error(f"Error creating session: {e}")
            raise
    
    def validate_session(self, session_id: str) -> Optional[UserSession]:
        """
        Validate and refresh user session
        
        Args:
            session_id: Session identifier
            
        Returns:
            UserSession object if valid, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.session_id, s.user_id, u.username, u.role, 
                       s.created_at, s.expires_at, s.last_activity, s.remember_me
                FROM user_sessions s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.session_id = ? AND s.is_active = 1 AND u.is_active = 1
            """, (session_id,))
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Check if session expired
            expires_at = datetime.fromisoformat(row[5])
            if datetime.now() > expires_at:
                # Deactivate expired session
                cursor.execute("""
                    UPDATE user_sessions SET is_active = 0 WHERE session_id = ?
                """, (session_id,))
                conn.commit()
                conn.close()
                return None
            
            # Update last activity
            now = datetime.now()
            cursor.execute("""
                UPDATE user_sessions SET last_activity = ? WHERE session_id = ?
            """, (now.isoformat(), session_id))
            
            conn.commit()
            conn.close()
            
            session = UserSession(
                session_id=row[0],
                user_id=row[1],
                username=row[2],
                role=row[3],
                created_at=datetime.fromisoformat(row[4]),
                expires_at=expires_at,
                last_activity=now,
                remember_me=bool(row[7]) if len(row) > 7 else False
            )
            
            return session
            
        except Exception as e:
            self.logger.error(f"Error validating session: {e}")
            return None
    
    def logout(self, session_id: str) -> bool:
        """
        Logout user by deactivating session
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_sessions SET is_active = 0 WHERE session_id = ?
            """, (session_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"User logged out: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error logging out user: {e}")
            return False
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID
        
        Args:
            user_id: User identifier
            
        Returns:
            User object if found, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT user_id, username, email, full_name, role, 
                       created_at, last_login, is_active, preferences
                FROM users WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return User(
                user_id=row[0],
                username=row[1],
                email=row[2],
                full_name=row[3],
                role=row[4],
                created_at=datetime.fromisoformat(row[5]),
                last_login=datetime.fromisoformat(row[6]) if row[6] else None,
                is_active=bool(row[7])
            )
            
        except Exception as e:
            self.logger.error(f"Error getting user by ID: {e}")
            return None
    
    def list_users(self, active_only: bool = True) -> List[User]:
        """
        List all users
        
        Args:
            active_only: Only return active users
            
        Returns:
            List of User objects
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = """
                SELECT user_id, username, email, full_name, role, 
                       created_at, last_login, is_active, preferences
                FROM users
            """
            
            if active_only:
                query += " WHERE is_active = 1"
            
            query += " ORDER BY created_at DESC"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()
            
            users = []
            for row in rows:
                users.append(User(
                    user_id=row[0],
                    username=row[1],
                    email=row[2],
                    full_name=row[3],
                    role=row[4],
                    created_at=datetime.fromisoformat(row[5]),
                    last_login=datetime.fromisoformat(row[6]) if row[6] else None,
                    is_active=bool(row[7])
                ))
            
            return users
            
        except Exception as e:
            self.logger.error(f"Error listing users: {e}")
            return []
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            cursor.execute("""
                UPDATE user_sessions 
                SET is_active = 0 
                WHERE expires_at < ? AND is_active = 1
            """, (now,))
            
            expired_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if expired_count > 0:
                self.logger.info(f"Cleaned up {expired_count} expired sessions")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up sessions: {e}")
    
    def save_conversation(self, user_id: str, conversation_id: str, title: str, 
                         thread_id: str, messages: List[dict], welcome_shown: bool = False) -> bool:
        """
        Save or update a user's conversation to database
        
        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            title: Conversation title
            thread_id: LangGraph thread ID
            messages: List of conversation messages
            welcome_shown: Whether welcome message was shown
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            # Insert or update conversation
            cursor.execute("""
                INSERT OR REPLACE INTO user_conversations 
                (conversation_id, user_id, title, thread_id, created_at, updated_at, is_active, welcome_shown)
                VALUES (?, ?, ?, ?, 
                    COALESCE((SELECT created_at FROM user_conversations WHERE conversation_id = ?), ?),
                    ?, 1, ?)
            """, (conversation_id, user_id, title, thread_id, conversation_id, now, now, welcome_shown))
            
            # Clear existing messages for this conversation
            cursor.execute("""
                DELETE FROM conversation_messages WHERE conversation_id = ?
            """, (conversation_id,))
            
            # Insert messages
            for message in messages:
                message_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO conversation_messages (message_id, conversation_id, role, content, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (message_id, conversation_id, message['role'], message['content'], now))
            
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Saved conversation {conversation_id} for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving conversation: {e}")
            return False
    
    def load_user_conversations(self, user_id: str) -> Dict:
        """
        Load all conversations for a user from database
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary of conversations in session state format
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get conversations
            cursor.execute("""
                SELECT conversation_id, title, thread_id, welcome_shown, created_at
                FROM user_conversations 
                WHERE user_id = ? AND is_active = 1
                ORDER BY created_at DESC
            """, (user_id,))
            
            conversations_data = cursor.fetchall()
            conversations = {}
            
            for conv_data in conversations_data:
                conversation_id, title, thread_id, welcome_shown, created_at = conv_data
                
                # Get messages for this conversation
                cursor.execute("""
                    SELECT role, content FROM conversation_messages 
                    WHERE conversation_id = ? 
                    ORDER BY created_at ASC
                """, (conversation_id,))
                
                messages = []
                for msg_row in cursor.fetchall():
                    messages.append({"role": msg_row[0], "content": msg_row[1]})
                
                # Use a more readable key format
                conv_key = f"conversation {len(conversations) + 1}"
                conversations[conv_key] = {
                    "conversation_id": conversation_id,
                    "thread_id": thread_id,
                    "title": title,
                    "messages": messages,
                    "welcome_shown": bool(welcome_shown)
                }
            
            conn.close()
            
            # If no conversations found, return empty dict (will trigger creation of default conversation)
            if not conversations:
                return {}
            
            self.logger.debug(f"Loaded {len(conversations)} conversations for user {user_id}")
            return conversations
            
        except Exception as e:
            self.logger.error(f"Error loading conversations for user {user_id}: {e}")
            return {}
    
    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        """
        Delete a user's conversation from database
        
        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verify conversation belongs to user
            cursor.execute("""
                SELECT conversation_id FROM user_conversations 
                WHERE conversation_id = ? AND user_id = ?
            """, (conversation_id, user_id))
            
            if not cursor.fetchone():
                self.logger.warning(f"Conversation {conversation_id} not found for user {user_id}")
                return False
            
            # Delete messages first (cascade)
            cursor.execute("""
                DELETE FROM conversation_messages WHERE conversation_id = ?
            """, (conversation_id,))
            
            # Delete conversation
            cursor.execute("""
                UPDATE user_conversations SET is_active = 0 WHERE conversation_id = ?
            """, (conversation_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Deleted conversation {conversation_id} for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting conversation: {e}")
            return False


# Global user manager instance
_user_manager: Optional[UserManager] = None


def get_user_manager() -> UserManager:
    """Get the global user manager instance"""
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager