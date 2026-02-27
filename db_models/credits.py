"""
Credits Model
Manages user credits for image generation
"""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timedelta
import uuid
from database import Base


class Credits(Base):
    """User credits/quota model"""
    __tablename__ = "credits"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Credit balances
    credits_remaining = Column(Float, default=0.0)  # Available credits
    credits_used_total = Column(Float, default=0.0)  # Lifetime usage
    
    # Monthly limits (for subscription tiers)
    credits_monthly_limit = Column(Float, default=10.0)  # Default free tier: 10 credits/month
    credits_monthly_used = Column(Float, default=0.0)
    
    # Subscription info
    subscription_tier = Column(String(20), default="free")  # free, pro, premium
    renewal_date = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Credits(user_id={self.user_id}, remaining={self.credits_remaining})>"
    
    def has_credits(self, amount: float = 1.0) -> bool:
        """Check if user has enough credits"""
        return self.credits_remaining >= amount
    
    def deduct_credits(self, amount: float):
        """Deduct credits from user account"""
        if self.has_credits(amount):
            self.credits_remaining -= amount
            self.credits_used_total += amount
            self.credits_monthly_used += amount
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def add_credits(self, amount: float):
        """Add credits to user account"""
        self.credits_remaining += amount
        self.updated_at = datetime.utcnow()
    
    def reset_monthly(self):
        """Reset monthly usage (call on renewal date)"""
        self.credits_monthly_used = 0.0
        self.credits_remaining = self.credits_monthly_limit
        self.renewal_date = datetime.utcnow() + timedelta(days=30)
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "credits_remaining": self.credits_remaining,
            "credits_used_total": self.credits_used_total,
            "credits_monthly_limit": self.credits_monthly_limit,
            "credits_monthly_used": self.credits_monthly_used,
            "subscription_tier": self.subscription_tier,
            "renewal_date": self.renewal_date.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
