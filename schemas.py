"""
Pydantic Schemas for API Request/Response Validation
Used by FastAPI for automatic validation and documentation
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


# =======================
# User Schemas
# =======================

class UserRegister(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "john_doe",
                "password": "securepassword123"
            }
        }


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class UserResponse(BaseModel):
    """Schema for user response"""
    id: UUID
    email: str
    username: str
    subscription_tier: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "username": "john_doe",
                "subscription_tier": "free",
                "is_active": True,
                "created_at": "2026-02-26T10:30:00",
                "last_login": "2026-02-26T15:45:00"
            }
        }


class UserUpdate(BaseModel):
    """Schema for user profile update"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    settings: Optional[dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "new_username",
                "settings": {"theme": "dark"}
            }
        }


# =======================
# Authentication Schemas
# =======================

class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "username": "john_doe",
                    "subscription_tier": "free",
                    "is_active": True,
                    "created_at": "2026-02-26T10:30:00"
                }
            }
        }


class TokenRefresh(BaseModel):
    """Schema for token refresh"""
    refresh_token: str


# =======================
# Credits Schemas
# =======================

class CreditsResponse(BaseModel):
    """Schema for credits response"""
    id: UUID
    user_id: UUID
    credits_remaining: float
    credits_used_total: float
    credits_monthly_limit: float
    credits_monthly_used: float
    subscription_tier: str
    renewal_date: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "credits_remaining": 10.0,
                "credits_used_total": 5.0,
                "credits_monthly_limit": 10.0,
                "credits_monthly_used": 5.0,
                "subscription_tier": "free",
                "renewal_date": "2026-03-26T10:30:00"
            }
        }


class CreditsAdd(BaseModel):
    """Schema for adding credits"""
    amount: float = Field(..., gt=0)
    reason: str = Field(..., max_length=200)


# =======================
# Error Schemas
# =======================

class ErrorResponse(BaseModel):
    """Schema for error response"""
    error: str
    message: str
    status_code: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "unauthorized",
                "message": "Invalid credentials",
                "status_code": 401
            }
        }


class SuccessResponse(BaseModel):
    """Schema for generic success response"""
    success: bool
    message: str
    data: Optional[dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {}
            }
        }


# =======================
# Usage Log Schemas
# =======================

class UsageLogResponse(BaseModel):
    """Schema for usage log response"""
    id: UUID
    user_id: UUID
    endpoint: str
    status: str
    credits_deducted: float
    generation_time: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440002",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "endpoint": "/v1/engine/generate/",
                "status": "success",
                "credits_deducted": 1.0,
                "generation_time": 45.3,
                "created_at": "2026-02-26T10:30:00",
                "completed_at": "2026-02-26T10:31:00"
            }
        }


# =======================
# Image Generation Schemas
# =======================

class GenerateImageRequest(BaseModel):
    """Schema for image generation request"""
    prompt: str = Field(..., min_length=1, max_length=2000)
    negative_prompt: Optional[str] = Field(None, max_length=2000)
    image_number: Optional[int] = Field(1, ge=1, le=4)
    style: Optional[str] = None
    
    # Fooocus API parameters
    performance_selection: Optional[str] = Field("Speed", description="Speed, Quality, Lightning, etc.")
    style_selections: Optional[list[str]] = Field(None, description="Fooocus styles like ['Fooocus V2', 'Fooocus Enhance']")
    sharpness: Optional[float] = Field(2.0, ge=0.0, le=30.0, description="Image sharpness 0-30")
    guidance_scale: Optional[float] = Field(4.0, ge=1.0, le=30.0, description="CFG scale 1-30")
    base_model_name: Optional[str] = None
    aspect_ratio: Optional[str] = None
    output_format: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "beautiful landscape with mountains",
                "negative_prompt": "blur, low quality",
                "image_number": 1,
                "style": "realistic",
                "performance_selection": "Speed",
                "style_selections": ["Fooocus V2", "Fooocus Enhance"],
                "sharpness": 2.0,
                "guidance_scale": 4.0
            }
        }
