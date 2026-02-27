"""
User Model
Stores user account information
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from database import Base


class User(Base):
    """User account model"""
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hash
    
    # Account status
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    
    # API authentication
    api_key = Column(String(64), unique=True, nullable=True, index=True)
    
    # Subscription
    subscription_tier = Column(
        String(20),
        default="free",
        nullable=False
    )  # free, pro, premium
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # User preferences
    settings = Column(JSON, default={})  # Store user preferences
    
    # Age Verification (LEGAL COMPLIANCE - Required for adult content)
    is_verified = Column(Boolean, default=False)  # True = user verified as 18+
    verification_method = Column(String(50), nullable=True)  # e.g., "yoti", "veriff", "persona"
    verified_at = Column(DateTime, nullable=True)
    verification_expires_at = Column(DateTime, nullable=True)  # Re-verification may be required
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username}, is_verified={self.is_verified})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "subscription_tier": self.subscription_tier,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "settings": self.settings,
        }
