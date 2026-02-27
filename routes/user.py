"""
User Profile Routes
Handles user profile management and settings
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from database import get_db
from db_models.user import User
from security import APIKeyHandler, JWTHandler
from schemas import UserResponse, UserUpdate, SuccessResponse
from middleware.auth import get_current_user

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user profile information
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        subscription_tier=current_user.subscription_tier,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user profile information
    """
    
    # Update username if provided
    if profile_data.username:
        # Check if new username is already taken
        existing = db.query(User).filter(
            User.username == profile_data.username,
            User.id != current_user.id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken"
            )
        
        current_user.username = profile_data.username
    
    # Update settings if provided
    if profile_data.settings:
        current_user.settings = profile_data.settings
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        subscription_tier=current_user.subscription_tier,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )


@router.get("/api-key")
async def get_api_key(
    current_user: User = Depends(get_current_user)
):
    """
    Get current API key
    """
    return {
        "api_key": current_user.api_key,
        "created_at": current_user.created_at.isoformat()
    }


@router.post("/api-key/regenerate")
async def regenerate_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a new API key (old one becomes invalid)
    """
    
    # Generate new API key
    new_api_key = APIKeyHandler.generate_api_key()
    current_user.api_key = new_api_key
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "success": True,
        "message": "API key regenerated successfully",
        "api_key": new_api_key,
        "warning": "Old API key is now invalid"
    }


@router.delete("/account", status_code=204)
async def delete_account(
    password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user account (requires password confirmation)
    """
    from security import PasswordHandler
    
    # Verify password
    if not PasswordHandler.verify_password(password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    # Delete user (cascade deletes credits and usage logs)
    db.delete(current_user)
    db.commit()
    
    return None  # 204 No Content
