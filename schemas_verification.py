"""
Age Verification Schemas
Pydantic models for age verification requests/responses
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class VerificationStatusResponse(BaseModel):
    """Age verification status response"""
    is_verified: bool
    verification_method: Optional[str] = None
    verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    requires_reverification: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_verified": True,
                "verification_method": "yoti",
                "verified_at": "2026-02-26T10:30:00",
                "expires_at": "2027-02-26T10:30:00",
                "requires_reverification": False
            }
        }


class AgeVerificationRecord(BaseModel):
    """Age verification record from history"""
    id: UUID
    provider: str  # yoti, veriff, persona, etc.
    status: str  # pending, approved, rejected, expired
    verified_country: Optional[str] = None
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_valid: bool
    days_until_expiration: int
    
    class Config:
        from_attributes = True


class YotiInitiateResponse(BaseModel):
    """Response from initiating Yoti verification"""
    status: str = Field(..., description="initiated or already_verified")
    provider: str = "yoti"
    verification_id: Optional[str] = None
    session_url: Optional[str] = None
    message: Optional[str] = None


class YotiCallbackRequest(BaseModel):
    """Yoti callback payload"""
    verification_id: UUID
    yoti_session_id: str
    status_code: str  # SUCCESS, FAILURE


class VeriffInitiateResponse(BaseModel):
    """Response from initiating Veriff verification"""
    status: str
    provider: str = "veriff"
    verification_id: Optional[str] = None
    session_url: Optional[str] = None


class PersonaInitiateResponse(BaseModel):
    """Response from initiating Persona verification"""
    status: str
    provider: str = "persona"
    verification_id: Optional[str] = None
    inquiry_token: Optional[str] = None


class AdminVerifyRequest(BaseModel):
    """Admin manual verification request"""
    user_id: UUID
    notes: str = Field(default="", max_length=500)


class FlagForReviewRequest(BaseModel):
    """Flag verification for admin review"""
    verification_id: UUID
    reason: str = Field(..., max_length=1000)
