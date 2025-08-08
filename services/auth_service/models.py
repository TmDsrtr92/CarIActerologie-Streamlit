"""
User and session data models for the authentication service.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class User:
    """User data model"""
    user_id: str
    username: str
    email: str
    full_name: str
    role: str = "user"  # user, admin, moderator, guest
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