"""Quick database verification"""
from database import SessionLocal
from db_models.user import User
from db_models.credits import Credits
from db_models.usage_log import UsageLog

db = SessionLocal()

print("\n=== DATABASE VERIFICATION ===\n")

# Recent users
users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
print(f"📊 Total Users in DB: {db.query(User).count()}")
print(f"\nRecent 5 Users:")
for u in users:
    credits_obj = db.query(Credits).filter(Credits.user_id == u.id).first()
    credits = credits_obj.credits_remaining if credits_obj else 0
    print(f"  • {u.email} | Credits: {credits} | Created: {u.created_at.strftime('%Y-%m-%d %H:%M')}")

# Recent usage logs
logs = db.query(UsageLog).order_by(UsageLog.timestamp.desc()).limit(5).all()
print(f"\n📝 Total Usage Logs: {db.query(UsageLog).count()}")
print(f"\nRecent 5 Usage Logs:")
for l in logs:
    print(f"  • {l.endpoint} | Credits: {l.credits_deducted} | Status: {l.status} | {l.timestamp.strftime('%H:%M:%S')}")

# Credit statistics
total_credits = db.query(Credits).all()
total_remaining = sum(c.credits_remaining for c in total_credits)
total_used = sum(c.credits_used_total for c in total_credits)
print(f"\n💰 Credit Statistics:")
print(f"  • Total Credits Remaining: {total_remaining}")
print(f"  • Total Credits Used: {total_used}")

db.close()
print("\n✅ Database verification complete!\n")
