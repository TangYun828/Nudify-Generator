"""
Authentication Middleware
JWT token validation and user injection
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session

from database import get_db
from db_models.user import User
from security import JWTHandler

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Extract and validate JWT token from Authorization header
    Returns current user or raises HTTPException
    
    Usage in routes:
    @router.get("/protected")
    async def protected_route(current_user: User = Depends(get_current_user)):
        return {"user_id": current_user.id}
    """
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Validate token
    user_id = JWTHandler.verify_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    
    return user


async def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: HTTPAuthCredentials = Depends(security) = None
) -> User | None:
    """
    Optional user authentication
    Returns user if token is valid, None otherwise
    
    Usage in routes:
    @router.get("/optional-auth")
    async def optional_route(user: User | None = Depends(get_current_user_optional)):
        if user:
            return {"user_id": user.id}
        else:
            return {"message": "Anonymous request"}
    """
    
    if not credentials:
        return None
    
    token = credentials.credentials
    user_id = JWTHandler.verify_token(token)
    
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    return user if user and user.is_active else None


async def verify_api_key(
    api_key: str,
    db: Session = Depends(get_db)
) -> User:
    """
    Verify API key and return user
    Alternative to JWT authentication
    
    Usage in routes:
    @router.post("/api/generate")
    async def generate(user: User = Depends(lambda key=Header(...): verify_api_key(key))):
        return {"user_id": user.id}
    """
    
    user = db.query(User).filter(User.api_key == api_key).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return user
