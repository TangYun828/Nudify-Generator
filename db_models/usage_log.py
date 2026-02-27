"""
Usage Log Model
Tracks user image generation requests and usage
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from database import Base


class UsageLog(Base):
    """Usage tracking model for image generation"""
    __tablename__ = "usage_logs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to user
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Request details
    endpoint = Column(String(100), nullable=False)  # e.g., /v1/engine/generate
    method = Column(String(10), nullable=False)  # POST, GET, etc.
    
    # Image generation parameters
    prompt = Column(String(1000), nullable=True)
    negative_prompt = Column(String(1000), nullable=True)
    image_count = Column(Integer, default=1)
    aspect_ratio = Column(String(20), nullable=True)  # e.g., "1024x1024"
    
    # Usage metrics
    credits_deducted = Column(Float, default=1.0)
    generation_time_seconds = Column(Float, nullable=True)
    
    # Status
    status = Column(String(20), default="pending")  # pending, success, failed
    error_message = Column(String(500), nullable=True)
    
    # Response info
    output_image_count = Column(Integer, default=0)
    output_size_mb = Column(Float, nullable=True)
    
    # Additional data
    request_metadata = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<UsageLog(user_id={self.user_id}, status={self.status})>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "endpoint": self.endpoint,
            "method": self.method,
            "prompt": self.prompt,
            "image_count": self.image_count,
            "credits_deducted": self.credits_deducted,
            "generation_time": self.generation_time_seconds,
            "status": self.status,
            "error_message": self.error_message,
            "output_image_count": self.output_image_count,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
