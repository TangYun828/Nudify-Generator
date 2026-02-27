# Complete File Inventory & Directory Structure

## Overview

Your nudify-backend project is now complete with production-ready code. Here's the complete file structure and purpose of each file.

---

## Directory Structure

```
C:\working folder\intimai\nudify-backend\
├── database.py                          # Supabase connection & ORM setup
├── security.py                          # JWT, bcrypt, API key handlers
├── schemas.py                           # Pydantic models for auth/user
├── schemas_verification.py              # Pydantic models for age verification
├── setup_db.py                          # Database initialization script
│
├── db_models/
│   ├── __init__.py                      # Package exports
│   ├── user.py                          # User ORM model
│   ├── credits.py                       # Credits/quota ORM model
│   ├── usage_log.py                     # Usage tracking ORM model
│   └── age_verification.py              # Age verification ORM model
│
├── routes/
│   ├── __init__.py                      # Package exports
│   ├── auth.py                          # Auth endpoints (register, login, refresh)
│   ├── user.py                          # User endpoints (profile, API key)
│   ├── credits.py                       # Credits endpoints (balance, usage)
│   └── verification.py                  # Age verification endpoints
│
├── middleware/
│   ├── __init__.py                      # Package exports
│   └── auth.py                          # JWT validation middleware
│
├── Documentation/
│   ├── SUPABASE_SETUP.md                # Database setup guide
│   ├── DATABASE_SETUP_COMPLETE.md       # Phase 1 summary
│   ├── AUTHENTICATION_API_COMPLETE.md   # Auth system documentation
│   ├── API_ENDPOINTS_REFERENCE.md       # API documentation with examples
│   ├── PHASE2_COMPLETE.md               # Phase 2 summary
│   ├── AGE_VERIFICATION_COMPLIANCE.md   # Legal requirements & compliance
│   ├── PHASE3_AGE_VERIFICATION_COMPLETE.md  # Phase 3 summary
│   ├── INTEGRATION_GUIDE.md             # Handler.py integration guide
│   ├── OPTIMIZED_ARCHITECTURE.md        # System architecture overview
│   ├── MIGRATION_MERGE_STRATEGY.md      # Step-by-step merge instructions (NEW)
│   ├── QUICK_MERGE_CHECKLIST.md         # Quick reference checklist (NEW)
│   ├── COMPLETE_ROADMAP.md              # Implementation roadmap (NEW)
│   ├── TROUBLESHOOTING.md               # Common issues & solutions (NEW)
│   └── FILE_INVENTORY.md                # This file
│
└── requirements_versions.txt            # Python dependencies
```

---

## File Descriptions

### Core Application Files

#### `database.py`
**Purpose:** Database connection and session management  
**Contents:**
- PostgreSQL connection string builder
- SQLAlchemy engine configuration
- Session factory (SessionLocal)
- Database initialization function
- Connection pooling settings

**When to use:**
- Import in handler.py for database initialization
- Called in @app.on_event("startup")

**Key classes/functions:**
- `get_db()` - Dependency injection for FastAPI
- `init_db()` - Creates all tables
- `engine` - SQLAlchemy database engine

---

#### `security.py`
**Purpose:** Authentication and security utilities  
**Contents:**
- Password hashing (bcrypt)
- JWT token creation and validation
- API key generation

**When to use:**
- Import in routes/auth.py for password hashing
- Import in middleware/auth.py for token validation

**Key classes:**
- `PasswordHandler` - bcrypt password operations
- `JWTHandler` - JWT token operations
- `APIKeyHandler` - API key generation/validation

---

#### `schemas.py`
**Purpose:** API request/response validation models  
**Contents:**
- User registration/login schemas
- Token response schema
- User profile schema
- API key schema
- Credits/usage schemas

**When to use:**
- Import in route handlers for request/response validation
- FastAPI automatically validates against these

**Key classes:**
- `UserRegister` - Registration form validation
- `UserLogin` - Login form validation
- `TokenResponse` - JWT token response
- `CreditsResponse` - Credits balance response

---

#### `schemas_verification.py`
**Purpose:** Age verification API models  
**Contents:**
- Verification initiation request
- Verification status response
- Verification history schema
- Admin verification schema

**When to use:**
- Import in routes/verification.py for request/response validation

**Key classes:**
- `VerificationInitiateRequest` - Start verification request
- `VerificationStatusResponse` - Current verification status
- `VerificationHistoryResponse` - Verification history

---

#### `setup_db.py`
**Purpose:** Database initialization script  
**Contents:**
- Environment variable validation
- Database connection test
- Table creation
- Test user creation
- Error handling and logging

**When to use:**
- Run once after Supabase setup: `python setup_db.py`
- Run in RunPod pod after deployment
- Run again if tables accidentally deleted

**Output:**
```
✓ Environment variables
✓ Database connection test
✓ Database tables created
✓ Test user created
```

---

### Database Models (db_models/)

#### `db_models/__init__.py`
**Purpose:** Package initialization and exports  
**Exports:** All ORM models for easy importing

**Usage:**
```python
from db_models import User, Credits, UsageLog, AgeVerification
```

---

#### `db_models/user.py`
**Purpose:** User account ORM model  
**Key fields:**
- `id` (UUID) - Primary key
- `email` - Unique email address
- `username` - Username for login
- `password_hash` - Bcrypt hashed password
- `is_verified` - Age verification status
- `verification_method` - Which provider verified (yoti/veriff/persona)
- `verified_at` - Timestamp of verification
- `verification_expires_at` - Expiration date
- `api_key` - Generated API key
- `subscription_tier` - free/pro/enterprise
- `created_at` - Account creation timestamp
- `settings` - JSON column for user preferences

**Key methods:**
- `to_dict()` - Convert to dictionary for responses

**Relationships:**
- Has many Credits records
- Has many UsageLog records
- Has many AgeVerification records

---

#### `db_models/credits.py`
**Purpose:** User quota and credits ORM model  
**Key fields:**
- `id` (UUID) - Primary key
- `user_id` (UUID) - Foreign key to users
- `credits_remaining` - Current balance (float)
- `credits_monthly_limit` - Monthly quota
- `credits_used_this_month` - Usage tracker
- `subscription_tier` - free/pro/enterprise
- `renewal_date` - When monthly resets

**Key methods:**
- `has_credits(amount)` - Check if sufficient credits
- `deduct_credits(amount)` - Deduct and return new balance
- `add_credits(amount)` - Add credits (admin)
- `reset_monthly()` - Reset monthly quota (runs via cron)

**Usage example:**
```python
credits = db.query(Credits).filter(Credits.user_id == user_id).first()
if credits.has_credits(1.0):
    credits.deduct_credits(1.0)
    db.commit()
```

---

#### `db_models/usage_log.py`
**Purpose:** Track all API requests and image generations  
**Key fields:**
- `id` (UUID) - Primary key
- `user_id` (UUID) - Foreign key to users
- `endpoint` - API endpoint called
- `method` - HTTP method
- `prompt` - Image generation prompt
- `image_count` - Number of images generated
- `status` - success/failed/in_progress
- `generation_time_seconds` - Time to generate
- `credits_deducted` - Credits used
- `error_message` - If failed
- `metadata` - JSON for additional data
- `created_at` - When request made
- `completed_at` - When completed

**Usage:**
- Logs every generation for analytics
- Tracks user behavior
- Monitors API performance
- Helps with debugging

---

#### `db_models/age_verification.py`
**Purpose:** Age verification records for compliance  
**Key fields:**
- `id` (UUID) - Primary key
- `user_id` (UUID) - Foreign key to users
- `provider` - Enum: Yoti/Veriff/Persona/ManualAdmin
- `status` - Enum: Pending/Approved/Rejected/Flagged
- `verified_country` - Country of verification
- `initiated_at` - When verification started
- `completed_at` - When verification completed
- `expires_at` - Expiration date
- `flagged_for_review` - Manual review needed

**Enums:**
- `VerificationProvider` - yoti, veriff, persona, manual_admin
- `VerificationStatus` - pending, approved, rejected, flagged_for_review

**Usage:**
- Stores verification history per user
- One record per verification attempt
- Allows re-verification after expiration

---

### Routes (routes/)

#### `routes/__init__.py`
**Purpose:** Package initialization and route exports  
**Usage:**
```python
from routes import auth, user, credits, verification
app.include_router(auth.router)
```

---

#### `routes/auth.py`
**Purpose:** User authentication endpoints  
**Endpoints:**

1. **POST /auth/register**
   - Register new user
   - Creates user, credits, usage_log records
   - Returns user data + JWT token

2. **POST /auth/login**
   - Login existing user
   - Validates email/password
   - Returns JWT token

3. **POST /auth/refresh**
   - Refresh expired access token
   - Uses 7-day refresh token
   - Returns new access token

4. **POST /auth/logout**
   - Logout user (optional, for frontend state)
   - Can invalidate token via blacklist

**Test:**
```bash
curl -X POST http://localhost:7866/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","username":"user","password":"pass"}'
```

---

#### `routes/user.py`
**Purpose:** User profile and settings endpoints  
**Endpoints:**

1. **GET /user/profile**
   - Get logged-in user's profile
   - Requires JWT token
   - Returns user details

2. **PUT /user/profile**
   - Update user profile
   - Can change username, settings
   - Requires JWT token

3. **GET /user/api-key**
   - Get user's API key
   - For backend API authentication
   - Requires JWT token

4. **POST /user/api-key/regenerate**
   - Generate new API key
   - Invalidates old key
   - Requires JWT token

5. **DELETE /user/account**
   - Delete user account
   - Soft delete or hard delete
   - Requires password confirmation

**Test:**
```bash
token="<JWT_TOKEN>"
curl -H "Authorization: Bearer $token" http://localhost:7866/user/profile
```

---

#### `routes/credits.py`
**Purpose:** Credits/quota management endpoints  
**Endpoints:**

1. **GET /credits/balance**
   - Get current credit balance
   - Requires JWT token

2. **GET /credits/usage/today**
   - Usage in current day
   - Requires JWT token

3. **GET /credits/usage/history**
   - Usage history (paginated)
   - Requires JWT token

4. **GET /credits/usage/stats**
   - Usage statistics
   - Charts, graphs data
   - Requires JWT token

5. **POST /credits/manual-add**
   - Admin only: Add credits to user
   - For manual adjustments
   - Requires admin token

**Test:**
```bash
token="<JWT_TOKEN>"
curl -H "Authorization: Bearer $token" http://localhost:7866/credits/balance
```

---

#### `routes/verification.py`
**Purpose:** Age verification endpoints (11 total)  
**Endpoints:**

**Status & History:**
- **GET /verification/status** - Current verification status
- **GET /verification/history** - Verification history

**Provider Initiation:**
- **POST /verification/yoti/initiate** - Start Yoti verification
- **POST /verification/veriff/initiate** - Start Veriff verification
- **POST /verification/persona/initiate** - Start Persona verification

**Provider Callbacks:**
- **POST /verification/yoti/callback** - Receive Yoti webhook
- **POST /verification/veriff/callback** - Receive Veriff webhook
- **POST /verification/persona/callback** - Receive Persona webhook

**Admin:**
- **POST /verification/admin/verify** - Manually verify user
- **POST /verification/admin/flag-for-review** - Flag for manual review

**Test:**
```bash
token="<JWT_TOKEN>"
curl -H "Authorization: Bearer $token" http://localhost:7866/verification/status
```

---

### Middleware (middleware/)

#### `middleware/__init__.py`
**Purpose:** Package initialization  

---

#### `middleware/auth.py`
**Purpose:** JWT and API key validation middleware  
**Key functions:**

1. **get_current_user()**
   - Extracts and validates JWT token
   - Returns current User object
   - Use: `@app.get("/protected", dependencies=[Depends(get_current_user)])`

2. **get_current_user_optional()**
   - Same as above but doesn't fail if no token
   - Returns None if no token
   - For endpoints that work with or without auth

3. **verify_api_key()**
   - Validates API key from header
   - Returns User object
   - Use: `@app.get("/api", dependencies=[Depends(verify_api_key)])`

**Usage in routes:**
```python
@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return current_user.to_dict()
```

---

### Configuration Files

#### `requirements_versions.txt`
**Purpose:** Python package dependencies  
**Key packages:**
- FastAPI 0.109.0 - Web framework
- SQLAlchemy 2.0.23 - ORM
- psycopg2-binary 2.9.9 - PostgreSQL driver
- PyJWT 2.8.1 - JWT tokens
- passlib 1.7.4 - Password hashing
- bcrypt 4.1.1 - Encryption
- Uvicorn 0.27.0 - ASGI server
- Pydantic 2.0+ - Data validation

**Installation:**
```bash
pip install -r requirements_versions.txt
```

---

## Documentation Files

### Getting Started
| File | Purpose | When to Read |
|------|---------|--------------|
| [QUICK_MERGE_CHECKLIST.md](QUICK_MERGE_CHECKLIST.md) | Fast implementation checklist | Before starting, during implementation |
| [COMPLETE_ROADMAP.md](COMPLETE_ROADMAP.md) | Full implementation plan | To understand complete process |
| [SUPABASE_SETUP.md](../SUPABASE_SETUP.md) | Database setup guide | First step, database configuration |

### Technical Documentation
| File | Purpose | When to Read |
|------|---------|--------------|
| [MIGRATION_MERGE_STRATEGY.md](MIGRATION_MERGE_STRATEGY.md) | Detailed merge instructions | During code merge |
| [OPTIMIZED_ARCHITECTURE.md](../OPTIMIZED_ARCHITECTURE.md) | System architecture | To understand design |
| [AUTHENTICATION_API_COMPLETE.md](../AUTHENTICATION_API_COMPLETE.md) | Auth system details | Understanding JWT flow |
| [API_ENDPOINTS_REFERENCE.md](../API_ENDPOINTS_REFERENCE.md) | API documentation | Testing endpoints |
| [INTEGRATION_GUIDE.md](../INTEGRATION_GUIDE.md) | Handler.py integration | Merging code |

### Deployment & Compliance
| File | Purpose | When to Read |
|------|---------|--------------|
| [AGE_VERIFICATION_COMPLIANCE.md](../AGE_VERIFICATION_COMPLIANCE.md) | compliance requirements | Before deployment |
| [PHASE3_AGE_VERIFICATION_COMPLETE.md](../PHASE3_AGE_VERIFICATION_COMPLETE.md) | Verification summary | Understanding verification |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues & fixes | When something breaks |

---

## Implementation Checklist

Use this checklist to track your progress:

### Preparation
- [ ] Review COMPLETE_ROADMAP.md
- [ ] Review QUICK_MERGE_CHECKLIST.md
- [ ] Have Supabase credentials ready

### Phase 1: Database Setup
- [ ] Create Supabase project
- [ ] Get database credentials
- [ ] Create .env file
- [ ] Run `python setup_db.py`

### Phase 2: Code Merge
- [ ] Clone Nudify-Generator
- [ ] Copy all files from nudify-backend
- [ ] Merge handler.py
- [ ] Update requirements_versions.txt

### Phase 3: Local Testing
- [ ] Install dependencies
- [ ] Start server locally
- [ ] Test /health endpoint
- [ ] Test auth endpoints
- [ ] Test protected endpoints
- [ ] Verify database operations

### Phase 4: Frontend Integration
- [ ] Create login page
- [ ] Create register page
- [ ] Create verification modal
- [ ] Update API calls with auth

### Phase 5: Age Verification
- [ ] Choose provider
- [ ] Create provider account
- [ ] Get API credentials
- [ ] Implement webhooks
- [ ] Test verification flow

### Phase 6: Deployment
- [ ] Push code to GitHub
- [ ] Build Docker image
- [ ] Create RunPod pod
- [ ] Set environment variables
- [ ] Initialize remote database
- [ ] Test remote endpoints

---

## Quick Reference

### Common Commands

```bash
# Database
python setup_db.py                    # Initialize database
python -c "from database import init_db; init_db()"  # Just create tables

# Server
python handler.py                     # Start server
python -m uvicorn handler:app         # Start with uvicorn
python -c "from handler import app; print(app.routes)"  # List routes

# Testing
curl http://localhost:7866/health    # Health check
python -c "from database import SessionLocal; db = SessionLocal(); print('✓ DB OK')"

# Utilities
pip install -r requirements_versions.txt   # Install dependencies
python -m black handler.py               # Format code
python -m py_compile handler.py          # Check syntax
```

### Environment Variables

```bash
# Database
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_DB_PASSWORD=password
SUPABASE_KEY=key
DATABASE_URL=postgresql://...

# Security
SECRET_KEY=your_secret_key_here

# Verification (choose one provider)
YOTI_SDK_ID=id
YOTI_PEM_KEY=key
VERIFF_API_KEY=key
PERSONA_API_KEY=key

# Server
FOOOCUS_API_PORT=7866
DEBUG=False
```

---

## Support & Troubleshooting

**First step:** Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for your specific error

**Common issues:**
- Import errors → Check files are copied to correct location
- Database connection → Check .env file and Supabase credentials
- API not starting → Check requirements installed, dependencies resolved
- JWT errors → Check SECRET_KEY in .env
- Age verification not working → Check provider credentials in .env

**Still stuck?** Review the relevant documentation file for your step, or check earlier files in guides for examples.

---

## Next Steps

1. **Start here:** [COMPLETE_ROADMAP.md](COMPLETE_ROADMAP.md)
2. **Setup database:** [SUPABASE_SETUP.md](../SUPABASE_SETUP.md)
3. **Merge code:** [MIGRATION_MERGE_STRATEGY.md](MIGRATION_MERGE_STRATEGY.md)
4. **Test locally:** [QUICK_MERGE_CHECKLIST.md](QUICK_MERGE_CHECKLIST.md)
5. **Fix issues:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
6. **Deploy:** [COMPLETE_ROADMAP.md](COMPLETE_ROADMAP.md#phase-6-deploy-to-runpod)

---

**You have everything you need. Ready to build? 🚀**
