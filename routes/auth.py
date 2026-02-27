"""
Authentication Routes
Handles user registration, login, logout, and token refresh
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional

from database import get_db
from db_models.user import User
from db_models.credits import Credits
from security import PasswordHandler, JWTHandler, APIKeyHandler
from schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    UserResponse,
    SuccessResponse
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user account
    Returns JWT tokens and user info
    """
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=PasswordHandler.hash_password(user_data.password),
        api_key=APIKeyHandler.generate_api_key(),
        subscription_tier="free"
    )
    
    db.add(user)
    db.flush()  # Get user ID without committing
    
    # Create credits account for new user
    credits = Credits(
        user_id=user.id,
        credits_remaining=10.0,  # Free tier: 10 credits
        credits_monthly_limit=10.0,
        subscription_tier="free"
    )
    
    db.add(credits)
    db.commit()
    db.refresh(user)
    
    # Create tokens
    access_token = JWTHandler.create_access_token(data={"sub": str(user.id)})
    refresh_token = JWTHandler.create_refresh_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=1800,  # 30 minutes in seconds
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            subscription_tier=user.subscription_tier,
            is_active=user.is_active,
            created_at=user.created_at
        )
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password
    Returns JWT tokens and user info
    """
    
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not PasswordHandler.verify_password(
        credentials.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Update last login time
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token = JWTHandler.create_access_token(data={"sub": str(user.id)})
    refresh_token = JWTHandler.create_refresh_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=1800,
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            subscription_tier=user.subscription_tier,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login
        )
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    Returns new access token
    """
    
    # Verify refresh token
    payload = JWTHandler.decode_token(token_data.refresh_token)
    
    if "error" in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token
    access_token = JWTHandler.create_access_token(data={"sub": str(user.id)})
    new_refresh_token = JWTHandler.create_refresh_token(data={"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=1800,
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            subscription_tier=user.subscription_tier,
            is_active=user.is_active,
            created_at=user.created_at
        )
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout():
    """
    Logout user (invalidate tokens on client side)
    Frontend should delete stored tokens
    """
    return SuccessResponse(
        success=True,
        message="Logout successful. Please remove stored tokens from client."
    )
