# Complete Integration Guide: User Management + Age Verification

## 📊 System Overview

Your complete user management system with legal age verification now includes:

```
┌─────────────────────────────────────────────────────────┐
│   Frontend (HTML/Vue)                                   │
│  - Login page                                           │
│  - Register page                                        │
│  - Age verification modal                               │
│  - App.html (protected by auth)                         │
└──────────────────┬──────────────────────────────────────┘
                   │ JWT Token
                   ▼
┌─────────────────────────────────────────────────────────┐
│   API Gateway (handler.py / FastAPI)                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │ /auth (register, login, refresh, logout)         │  │
│  │ /user (profile, api-key)                         │  │
│  │ /credits (balance, usage, stats)                 │  │
│  │ /verification (yoti, veriff, persona, callback)  │  │
│  │ /v1/engine/generate (check is_verified)          │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────────┘
                   │ SQL Queries
                   ▼
┌─────────────────────────────────────────────────────────┐
│   Supabase PostgreSQL Database                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ users (id, email, is_verified, verification_*) │  │
│  │ credits (user_id, remaining, limit)              │  │
│  │ age_verifications (user_id, provider, status)    │  │
│  │ usage_logs (user_id, endpoint, status)           │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 🔗 How to Integrate into handler.py

### Current handler.py Structure

Your handler.py currently handles Fooocus image generation. We need to add:
1. FastAPI initialization
2. Database setup
3. Route registration
4. Middleware setup

### Step 1: Add Import Statements

Add to top of `handler.py`:

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import all routes
from routes import auth, user, credits, verification
from middleware.auth import get_current_user
from database import init_db, get_db, Base, engine
from db_models import User, Credits, AgeVerification, UsageLog
```

### Step 2: Initialize FastAPI App

```python
# Create FastAPI application
app = FastAPI(
    title="Nudify API",
    description="NSFW AI Image Generation with Age Verification",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup():
    print("Initializing database...")
    init_db()
    print("✓ Database ready")
    
    # Start Fooocus API as usual
    print("Starting Fooocus API...")
    # ... your existing Fooocus startup code
```

### Step 3: Register Routes

```python
# Include authentication routes
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(credits.router)
app.include_router(verification.router)

# Your existing /v1/engine/generate endpoint needs update
```

### Step 4: Update Image Generation Endpoint

The existing `/v1/engine/generate/` needs authentication:

```python
@app.post("/v1/engine/generate/")
async def generate_image(
    request: GenerateRequest,
    current_user: User = Depends(get_current_user),  # NEW: Require authentication
    db: Session = Depends(get_db)  # NEW: Database session
):
    """
    Generate NSFW image with authentication and age verification
    """
    
    # NEW: Check age verification (LEGAL REQUIREMENT)
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Age verification required before image generation",
            headers={"X-Requires-Verification": "true"}
        )
    
    # NEW: Check if verification is expired
    if current_user.verification_expires_at:
        if datetime.utcnow() > current_user.verification_expires_at:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Age verification expired, re-verification required"
            )
    
    # NEW: Check credits
    credits_record = db.query(Credits).filter(
        Credits.user_id == current_user.id
    ).first()
    
    if not credits_record or credits_record.credits_remaining < 1.0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits",
            headers={"X-Insufficient-Credits": "true"}
        )
    
    # NEW: Create usage log
    import time
    start_time = time.time()
    
    usage_log = UsageLog(
        user_id=current_user.id,
        endpoint="/v1/engine/generate/",
        method="POST",
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        image_count=request.image_number,
        aspect_ratio=request.aspect_ratio,
        status="in_progress"
    )
    db.add(usage_log)
    db.commit()
    
    try:
        # Your existing Fooocus generation code here
        # ... generate images ...
        
        # After successful generation:
        generation_time = time.time() - start_time
        
        # Deduct credits
        credits_to_use = request.image_number * 1.0  # 1 credit per image
        credits_record.deduct_credits(credits_to_use)
        
        # Update usage log
        usage_log.status = "success"
        usage_log.generation_time_seconds = generation_time
        usage_log.output_image_count = len(images)
        usage_log.completed_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "output": {"images": images},  # Your existing response
            "user": {
                "credits_remaining": credits_record.credits_remaining,
                "credits_used": credits_to_use
            }
        }
        
    except Exception as e:
        # Log failure
        usage_log.status = "failed"
        usage_log.error_message = str(e)
        usage_log.completed_at = datetime.utcnow()
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image generation failed"
        )
```

### Step 5: Add Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "version": "2.0.0",
        "services": {
            "api": "running",
            "database": "running",
            "fooocus": "running"
        }
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Nudify API",
        "version": "2.0.0",
        "endpoints": {
            "auth": "/auth/*",
            "user": "/user/*",
            "credits": "/credits/*",
            "verification": "/verification/*",
            "generate": "/v1/engine/generate",
            "docs": "/docs",
            "health": "/health"
        }
    }
```

---

## 🔄 Complete Flow Diagram

```
User Registration
    ↓
POST /auth/register
    ↓
User created in database
Credits account created (10 credits free tier)
JWT tokens returned
    ↓
User Sees Login Form
    ↓
POST /auth/login
    ↓
JWT Access Token + Refresh Token returned
    ↓
User Clicks "Generate Image"
    ↓
Frontend checks: GET /verification/status
    ↓ Response: is_verified = false
    ↓
Show Age Verification Modal
User selects provider (Yoti/Veriff/Persona)
    ↓
POST /verification/yoti/initiate
    ↓
Returns: { status_url: "https://yoti.com/share/..." }
    ↓
User redirected to Yoti in new window
User scans ID + Face
Yoti verifies (takes 1-5 seconds)
    ↓
Yoti redirects back to your site
    ↓
POST /verification/yoti/callback (from Yoti servers)
    ↓
UPDATE users SET is_verified = true
    ↓
User refreshes page, verification complete
    ↓
POST /v1/engine/generate/ with Bearer token
    ↓
Check: is_verified = true? ✓
Check: credits >= 1? ✓
    ↓
Generate image (takes 30-60 seconds)
    ↓
Deduct 1 credit
Log usage
Return image
    ↓
User can download image
Credits remaining shown
```

---

## 📋 Required Environment Variables

Create `.env` file:

```bash
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_DB_PASSWORD=your_password
SUPABASE_KEY=your_service_role_key

# JWT
SECRET_KEY=your_super_secret_key_change_in_production

# Fooocus
FOOOCUS_API_URL=http://127.0.0.1:7866
FOOOCUS_API_KEY=your_api_key

# Verification Provider (choose one or multiple)
YOTI_SDK_ID=your_yoti_sdk_id
YOTI_PEM_KEY=your_yoti_pem_key

VERIFF_API_KEY=your_veriff_api_key

PERSONA_API_KEY=your_persona_api_key
PERSONA_TEMPLATE_ID=your_template_id

# Server Config
API_PORT=7866
API_HOST=0.0.0.0
DEBUG=False
```

---

## 🧪 Testing the Complete System

### 1. Setup Database

```bash
python setup_db.py
```

Output should show:
- ✓ Environment variables
- ✓ Database connection
- ✓ Tables created
- ✓ Test user created

### 2. Start API Server

```bash
# Using handler.py
python handler.py

# Or using uvicorn
python -m uvicorn handler:app --reload --host 0.0.0.0 --port 7866
```

### 3. Test Endpoints

```bash
# 1. Check API is running
curl http://localhost:7866/health

# 2. Register new user
curl -X POST http://localhost:7866/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "username": "newuser",
    "password": "password123"
  }'

# Save the access_token from response

# 3. Try to generate image (should fail - not verified)
curl -X POST http://localhost:7866/v1/engine/generate/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test"}'

# Response: 403 Age verification required

# 4. Get verification status
curl -X GET http://localhost:7866/verification/status \
  -H "Authorization: Bearer <access_token>"

# Response: is_verified = false

# 5. Check API docs
# Open http://localhost:7866/docs in browser
```

---

## 📁 Final File Structure

```
nudify-backend/
├── handler.py                          # UPDATED: Main FastAPI app
├── database.py                         # Database connection
├── security.py                         # JWT & password
├── schemas.py                          # API schemas
├── schemas_verification.py             # Verification schemas
├── setup_db.py                         # DB initialization
├── 
├── db_models/
│   ├── __init__.py
│   ├── user.py                         # UPDATED: added is_verified
│   ├── credits.py
│   ├── usage_log.py
│   └── age_verification.py            # NEW
│
├── routes/
│   ├── __init__.py                     # UPDATED: added verification
│   ├── auth.py
│   ├── user.py
│   ├── credits.py
│   └── verification.py                 # NEW
│
├── middleware/
│   ├── __init__.py
│   └── auth.py
│
└── docs/
    ├── SUPABASE_SETUP.md
    ├── AUTHENTICATION_API_COMPLETE.md
    ├── AGE_VERIFICATION_COMPLIANCE.md   # NEW
    └── API_ENDPOINTS_REFERENCE.md
```

---

## ✅ Integration Checklist

### Database
- [x] User model with is_verified fields
- [x] AgeVerification model created
- [x] Credits model
- [x] UsageLog model
- [ ] Run setup_db.py to create tables

### Backend Routes
- [x] /auth/* endpoints
- [x] /user/* endpoints
- [x] /credits/* endpoints
- [x] /verification/* endpoints
- [ ] Update /v1/engine/generate/ for auth & credits

### Middleware
- [x] JWT validation
- [ ] Add to all protected endpoints

### Frontend
- [ ] Create login.html
- [ ] Create register.html
- [ ] Create verification modal
- [ ] Update app.html to require auth
- [ ] Store JWT tokens

### Testing
- [ ] Register new user
- [ ] Login
- [ ] Check verification status
- [ ] Try image generation (should fail)
- [ ] Complete age verification
- [ ] Try image generation (should work)

### Deployment
- [ ] Set environment variables
- [ ] Configure verification provider
- [ ] Update Terms & Privacy Policy
- [ ] Test in production
- [ ] Enable payment processing

---

## 🎯 Next Phase: Frontend Integration

After backend is integrated, create:

1. **login.html** - Login form
2. **register.html** - Registration form
3. **verification-modal.html** - Age verification UI
4. **dashboard.html** - User dashboard

These will integrate with the API using JavaScript JWT management and fetch API calls.

---

**Total Implementation Time: ~4-6 hours**

Ready to integrate? Let me know! 🚀
