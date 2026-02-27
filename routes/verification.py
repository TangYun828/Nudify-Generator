"""
Age Verification Routes
Handles third-party age verification integration for legal compliance
Required for adult content platforms in US (TX, FL, CA) and EU/UK (2026+)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from database import get_db
from db_models.user import User
from db_models.age_verification import AgeVerification, VerificationStatus, VerificationProvider
from middleware.auth import get_current_user
from schemas import SuccessResponse

router = APIRouter(prefix="/verification", tags=["age_verification"])


@router.get("/status")
async def get_verification_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current age verification status for user
    Required before accessing NSFW generation
    """
    
    return {
        "is_verified": current_user.is_verified,
        "verification_method": current_user.verification_method,
        "verified_at": current_user.verified_at.isoformat() if current_user.verified_at else None,
        "expires_at": current_user.verification_expires_at.isoformat() if current_user.verification_expires_at else None,
        "requires_reverification": (
            current_user.verification_expires_at and 
            datetime.utcnow() > current_user.verification_expires_at
        ) if current_user.verification_expires_at else False
    }


@router.get("/history")
async def get_verification_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's age verification history (for compliance audit)
    """
    
    verifications = db.query(AgeVerification).filter(
        AgeVerification.user_id == current_user.id
    ).order_by(
        AgeVerification.initiated_at.desc()
    ).all()
    
    return {
        "count": len(verifications),
        "verifications": [v.to_dict() for v in verifications]
    }


# ============================================================
# Yoti Integration
# ============================================================

@router.post("/yoti/initiate")
async def initiate_yoti_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiate Yoti age verification
    Returns Yoti session URL for user to complete verification
    """
    
    # Check if already verified and valid
    if current_user.is_verified and current_user.verification_method == "yoti":
        if current_user.verification_expires_at and datetime.utcnow() < current_user.verification_expires_at:
            return {
                "status": "already_verified",
                "message": "User already verified with Yoti",
                "expires_at": current_user.verification_expires_at.isoformat()
            }
    
    # Create verification record
    verification_record = AgeVerification(
        user_id=current_user.id,
        provider=VerificationProvider.YOTI,
        status=VerificationStatus.PENDING
    )
    
    db.add(verification_record)
    db.commit()
    
    # TODO: Call Yoti API to create session
    # yoti_session_url = create_yoti_session(user_id=str(current_user.id))
    
    return {
        "status": "initiated",
        "provider": "yoti",
        "verification_id": str(verification_record.id),
        "session_url": "https://yoti.com/share/...",  # Placeholder
        "message": "User should be redirected to this URL to complete verification"
    }


@router.post("/yoti/callback")
async def yoti_verification_callback(
    verification_id: UUID,
    yoti_session_id: str,
    status_code: str,  # SUCCESS, FAILURE
    db: Session = Depends(get_db)
):
    """
    Receive callback from Yoti after user completes verification
    Called by Yoti servers - no auth required
    """
    
    # Get verification record
    verification = db.query(AgeVerification).filter(
        AgeVerification.id == verification_id
    ).first()
    
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification record not found"
        )
    
    # Update based on Yoti response
    if status_code == "SUCCESS":
        verification.status = VerificationStatus.APPROVED
        verification.completed_at = datetime.utcnow()
        verification.provider_reference_id = yoti_session_id
        
        # Get user and update verification status
        user = db.query(User).filter(User.id == verification.user_id).first()
        user.is_verified = True
        user.verification_method = "yoti"
        user.verified_at = datetime.utcnow()
        # Yoti verification valid for 1 year
        user.verification_expires_at = datetime.utcnow() + timedelta(days=365)
        
    else:
        verification.status = VerificationStatus.REJECTED
        verification.completed_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "status": verification.status.value
    }


# ============================================================
# Veriff Integration
# ============================================================

@router.post("/veriff/initiate")
async def initiate_veriff_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiate Veriff age verification
    Returns Veriff session URL
    """
    
    if current_user.is_verified and current_user.verification_method == "veriff":
        if current_user.verification_expires_at and datetime.utcnow() < current_user.verification_expires_at:
            return {
                "status": "already_verified",
                "message": "User already verified with Veriff"
            }
    
    verification_record = AgeVerification(
        user_id=current_user.id,
        provider=VerificationProvider.VERIFF,
        status=VerificationStatus.PENDING
    )
    
    db.add(verification_record)
    db.commit()
    
    # TODO: Call Veriff API
    # veriff_url = create_veriff_session(...)
    
    return {
        "status": "initiated",
        "provider": "veriff",
        "verification_id": str(verification_record.id),
        "session_url": "https://www.veriff.com/...",  # Placeholder
    }


@router.post("/veriff/callback")
async def veriff_verification_callback(
    verification_id: UUID,
    veriff_session_id: str,
    status: str,  # approved, declined, expired, abandoned
    db: Session = Depends(get_db)
):
    """
    Receive callback from Veriff after verification
    """
    
    verification = db.query(AgeVerification).filter(
        AgeVerification.id == verification_id
    ).first()
    
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    
    if status == "approved":
        verification.status = VerificationStatus.APPROVED
        verification.completed_at = datetime.utcnow()
        
        user = db.query(User).filter(User.id == verification.user_id).first()
        user.is_verified = True
        user.verification_method = "veriff"
        user.verified_at = datetime.utcnow()
        user.verification_expires_at = datetime.utcnow() + timedelta(days=365)
    else:
        verification.status = VerificationStatus.REJECTED
        verification.completed_at = datetime.utcnow()
    
    db.commit()
    
    return {"success": True}


# ============================================================
# Persona Integration
# ============================================================

@router.post("/persona/initiate")
async def initiate_persona_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiate Persona age verification
    """
    
    if current_user.is_verified and current_user.verification_method == "persona":
        if current_user.verification_expires_at and datetime.utcnow() < current_user.verification_expires_at:
            return {"status": "already_verified"}
    
    verification_record = AgeVerification(
        user_id=current_user.id,
        provider=VerificationProvider.PERSONA,
        status=VerificationStatus.PENDING
    )
    
    db.add(verification_record)
    db.commit()
    
    # TODO: Call Persona API
    
    return {
        "status": "initiated",
        "provider": "persona",
        "verification_id": str(verification_record.id),
        "inquiry_token": "...",  # Placeholder
    }


@router.post("/persona/callback")
async def persona_verification_callback(
    verification_id: UUID,
    status: str,  # completed, approved, declined, etc.
    db: Session = Depends(get_db)
):
    """
    Receive callback from Persona
    """
    
    verification = db.query(AgeVerification).filter(
        AgeVerification.id == verification_id
    ).first()
    
    if not verification:
        raise HTTPException(status_code=404, detail="Not found")
    
    if status == "approved":
        verification.status = VerificationStatus.APPROVED
        verification.completed_at = datetime.utcnow()
        
        user = db.query(User).filter(User.id == verification.user_id).first()
        user.is_verified = True
        user.verification_method = "persona"
        user.verified_at = datetime.utcnow()
        user.verification_expires_at = datetime.utcnow() + timedelta(days=365)
    else:
        verification.status = VerificationStatus.REJECTED
        verification.completed_at = datetime.utcnow()
    
    db.commit()
    
    return {"success": True}


# ============================================================
# Admin: Manual Verification
# ============================================================

@router.post("/admin/verify")
async def admin_verify_user(
    user_id: UUID,
    notes: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ADMIN ONLY: Manually verify user for testing/customer service
    """
    
    # TODO: Add admin role check
    # if current_user.role != "admin":
    #     raise HTTPException(status_code=403, detail="Admin only")
    
    verification = AgeVerification(
        user_id=user_id,
        provider=VerificationProvider.MANUAL_ADMIN,
        status=VerificationStatus.APPROVED,
        completed_at=datetime.utcnow(),
        reviewed_by_admin=str(current_user.id),
        admin_notes=notes
    )
    
    db.add(verification)
    
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_verified = True
        user.verification_method = "manual_admin"
        user.verified_at = datetime.utcnow()
        user.verification_expires_at = datetime.utcnow() + timedelta(days=365)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"User {user_id} manually verified",
        "verified_at": verification.completed_at.isoformat()
    }


@router.post("/admin/flag-for-review")
async def flag_verification_for_review(
    verification_id: UUID,
    reason: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ADMIN ONLY: Flag a verification for manual review
    """
    
    verification = db.query(AgeVerification).filter(
        AgeVerification.id == verification_id
    ).first()
    
    if not verification:
        raise HTTPException(status_code=404, detail="Not found")
    
    verification.flagged_for_review = True
    verification.admin_notes = reason
    db.commit()
    
    return {
        "success": True,
        "message": "Verification flagged for review"
    }
