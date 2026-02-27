"""
Credits Management Routes
Handles user credits, quota, and subscription management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from database import get_db
from db_models.user import User
from db_models.credits import Credits
from db_models.usage_log import UsageLog
from schemas import CreditsResponse, SuccessResponse
from middleware.auth import get_current_user

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/balance", response_model=CreditsResponse)
async def get_credits_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's current credit balance
    """
    
    credits = db.query(Credits).filter(
        Credits.user_id == current_user.id
    ).first()
    
    if not credits:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credits account not found"
        )
    
    # Check if renewal date has passed
    if credits.renewal_date and datetime.utcnow() > credits.renewal_date:
        credits.reset_monthly()
        db.commit()
    
    return CreditsResponse(
        id=credits.id,
        user_id=credits.user_id,
        credits_remaining=credits.credits_remaining,
        credits_used_total=credits.credits_used_total,
        credits_monthly_limit=credits.credits_monthly_limit,
        credits_monthly_used=credits.credits_monthly_used,
        subscription_tier=credits.subscription_tier,
        renewal_date=credits.renewal_date
    )


@router.get("/usage/today")
async def get_today_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's credit usage for today
    """
    
    from datetime import date
    today = datetime.utcnow().date()
    
    usage = db.query(UsageLog).filter(
        UsageLog.user_id == current_user.id,
        UsageLog.status == "success"
    ).all()
    
    today_usage = [
        log for log in usage
        if log.created_at.date() == today
    ]
    
    total_credits = sum(log.credits_deducted for log in today_usage)
    
    return {
        "date": today.isoformat(),
        "requests": len(today_usage),
        "credits_used": total_credits,
        "credits_remaining": (db.query(Credits)
                             .filter(Credits.user_id == current_user.id)
                             .first().credits_remaining)
    }


@router.get("/usage/history")
async def get_usage_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's usage history (last N requests)
    """
    
    logs = db.query(UsageLog).filter(
        UsageLog.user_id == current_user.id
    ).order_by(
        desc(UsageLog.created_at)
    ).limit(limit).all()
    
    return {
        "count": len(logs),
        "usage_logs": [log.to_dict() for log in logs]
    }


@router.get("/usage/stats")
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's overall usage statistics
    """
    
    all_logs = db.query(UsageLog).filter(
        UsageLog.user_id == current_user.id,
        UsageLog.status == "success"
    ).all()
    
    credits = db.query(Credits).filter(
        Credits.user_id == current_user.id
    ).first()
    
    total_requests = len(all_logs)
    total_credits_used = sum(log.credits_deducted for log in all_logs)
    avg_generation_time = (
        sum(log.generation_time_seconds for log in all_logs 
            if log.generation_time_seconds) / len(all_logs)
        if all_logs else 0
    )
    
    return {
        "subscription_tier": credits.subscription_tier,
        "total_requests": total_requests,
        "total_credits_used": total_credits_used,
        "remaining_credits": credits.credits_remaining,
        "monthly_used": credits.credits_monthly_used,
        "monthly_limit": credits.credits_monthly_limit,
        "monthly_remaining": max(0, credits.credits_monthly_limit - credits.credits_monthly_used),
        "average_generation_time": round(avg_generation_time, 2),
        "renewal_date": credits.renewal_date.isoformat()
    }


@router.post("/manual-add")
async def add_credits_admin(
    user_id: str,
    amount: float,
    reason: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ADMIN ONLY: Add credits to user account
    (For testing, promotions, and customer service)
    """
    
    # TODO: Add admin role check
    # if current_user.role != "admin":
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    credits = db.query(Credits).filter(
        Credits.user_id == user_id
    ).first()
    
    if not credits:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User credits not found"
        )
    
    # Add credits
    credits.add_credits(amount)
    db.commit()
    
    return {
        "success": True,
        "message": f"Added {amount} credits to user",
        "reason": reason,
        "new_balance": credits.credits_remaining
    }
