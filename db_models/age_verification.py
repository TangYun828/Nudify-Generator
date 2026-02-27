"""
Age Verification Model
Tracks third-party identity verification for NSFW content compliance
Legal requirement in US (TX, FL, CA) and EU/UK jurisdictions (2026+)
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timedelta
import uuid
import enum
from database import Base


class VerificationProvider(str, enum.Enum):
    """Supported age verification providers"""
    YOTI = "yoti"
    VERIFF = "veriff"
    PERSONA = "persona"
    IDW = "idw"
    SOCURE = "socure"
    MANUAL_ADMIN = "manual_admin"  # For admin verification


class VerificationStatus(str, enum.Enum):
    """Age verification status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class AgeVerification(Base):
    """Age verification record - tracks identity verification events"""
    __tablename__ = "age_verifications"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), 
                     nullable=False, index=True)
    
    # Verification provider info
    provider = Column(Enum(VerificationProvider), nullable=False)  # yoti, veriff, persona, etc.
    provider_reference_id = Column(String(255), nullable=True)  # ID from verification provider
    
    # Verification status
    status = Column(Enum(VerificationStatus), default=VerificationStatus.PENDING)
    
    # Verification details
    verified_name = Column(String(255), nullable=True)  # Name from ID document
    verified_date_of_birth = Column(String(10), nullable=True)  # YYYY-MM-DD (encrypted in production)
    verified_country = Column(String(2), nullable=True)  # ISO country code
    
    # Verification evidence
    verification_data = Column(JSON, default={})  # Store additional provider data
    
    # Timestamps
    initiated_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # May need reverification
    
    # Audit trail
    reviewed_by_admin = Column(String(255), nullable=True)  # Admin user for manual reviews
    admin_notes = Column(String(500), nullable=True)
    
    # Flags
    is_current = Column(Boolean, default=True)  # Latest verification for user
    flagged_for_review = Column(Boolean, default=False)  # Manual review needed
    
    def __repr__(self):
        return f"<AgeVerification(user_id={self.user_id}, provider={self.provider}, status={self.status})>"
    
    def is_valid(self) -> bool:
        """Check if verification is still valid"""
        if self.status != VerificationStatus.APPROVED:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def days_until_expiration(self) -> int:
        """Days until verification expires (if set)"""
        if not self.expires_at:
            return -1  # No expiration
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "provider": self.provider.value,
            "status": self.status.value,
            "verified_country": self.verified_country,
            "initiated_at": self.initiated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_valid": self.is_valid(),
            "days_until_expiration": self.days_until_expiration(),
        }
