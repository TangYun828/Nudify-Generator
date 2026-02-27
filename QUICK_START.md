# Quick Start: Copy-Paste Commands

This document contains exact commands you can copy-paste to get everything running.

---

## Phase 1: Setup Supabase (First Time Only)

### Step 1: Go to Supabase
```
https://supabase.com → Sign up → Create new project
```

### Step 2: Get Credentials
In Supabase console:
1. Go to Settings → API
2. Copy `Project URL` → Your SUPABASE_URL
3. Go to Settings → Database → Connection String
4. Copy password → Your SUPABASE_DB_PASSWORD
5. Go to Settings → API → service_role secret → Your SUPABASE_KEY

### Step 3: Create .env File
Create file: `C:\working folder\intimai\nudify-backend\.env`

```
# Paste your values from Supabase
SUPABASE_URL=https://[your-project-id].supabase.co
SUPABASE_DB_PASSWORD=[your_password]
SUPABASE_KEY=[your_service_role_key]
DATABASE_URL=postgresql://postgres:[your_password]@db.supabase.co:5432/postgres

# Security
SECRET_KEY=your_super_secret_key_change_in_production_123456789

# Server
FOOOCUS_API_PORT=7866
DEBUG=False
```

---

## Phase 2: Initialize Database

**Location:** `C:\working folder\intimai\nudify-backend\`

```bash
# Change to project directory
cd "C:\working folder\intimai\nudify-backend"

# Create database tables and test user
python setup_db.py
```

**Expected output:**
```
✓ Environment variables loaded
✓ Database connection test successful
✓ Database tables created
✓ Test user created (email: test@example.com)
```

**If fails:**
- Check .env file values are correct
- Check internet connection
- Check Supabase project exists in console

---

## Phase 3: Clone Nudify-Generator

```bash
# Go to intimai folder
cd "C:\working folder\intimai"

# Clone Nudify-Generator
git clone https://github.com/TangYun828/Nudify-Generator.git

# Go into it
cd Nudify-Generator

# Create feature branch
git checkout -b feature/user-management-integration
```

---

## Phase 4: Copy Files

### Windows PowerShell (Recommended)

```powershell
# Go to Nudify-Generator directory
cd "C:\working folder\intimai\Nudify-Generator"

# Copy core files
Copy-Item -Path ..\nudify-backend\database.py -Destination .
Copy-Item -Path ..\nudify-backend\security.py -Destination .
Copy-Item -Path ..\nudify-backend\schemas.py -Destination .
Copy-Item -Path ..\nudify-backend\schemas_verification.py -Destination .
Copy-Item -Path ..\nudify-backend\setup_db.py -Destination .

# Copy directories
Copy-Item -Path ..\nudify-backend\db_models -Destination . -Recurse
Copy-Item -Path ..\nudify-backend\routes -Destination . -Recurse
Copy-Item -Path ..\nudify-backend\middleware -Destination . -Recurse

# Copy .env file
Copy-Item -Path ..\nudify-backend\.env -Destination .

# Verify files copied
Get-ChildItem database.py, security.py, setup_db.py
Get-ChildItem -Directory db_models, routes, middleware
```

---

## Phase 5: Update handler.py

**This requires manual editing.** Use MIGRATION_MERGE_STRATEGY.md as template.

Key points to add to handler.py:

```python
# At top of file, add imports:
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, get_db
from routes import auth, user, credits, verification

# After imports, create app:
app = FastAPI(title="Nudify API", version="2.0.0")

# Add CORS:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add startup event (must be before routes):
@app.on_event("startup")
async def startup():
    print("Initializing database...")
    init_db()

# Register routes (after startup):
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(credits.router)
app.include_router(verification.router)

# Add health endpoint:
@app.get("/health")
async def health():
    return {"status": "healthy"}

# Update the /v1/engine/generate/ endpoint to check:
# - Age verification (is_verified)
# - Credit balance
# - Deduct credits after generation
```

See [MIGRATION_MERGE_STRATEGY.md](MIGRATION_MERGE_STRATEGY.md#step-3-update-handlerpy) for complete template.

---

## Phase 6: Update requirements_versions.txt

Add these lines to `Nudify-Generator/requirements_versions.txt`:

```
# Database & ORM
sqlalchemy==2.0.23
psycopg2-binary==2.9.9

# Authentication & Security
PyJWT==2.8.1
passlib==1.7.4
bcrypt==4.1.1

# API & Validation
fastapi==0.109.0
uvicorn==0.27.0
email-validator==2.1.0
pydantic-email==2.0.0
```

---

## Phase 7: Local Testing

```bash
# Go to Nudify-Generator directory
cd "C:\working folder\intimai\Nudify-Generator"

# Install dependencies
pip install -r requirements_versions.txt

# Initialize database (creates tables)
python setup_db.py

# Start server
python handler.py
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:7866
```

---

## Phase 8: Test Endpoints

**In another terminal/PowerShell:**

```bash
# Health check
curl http://localhost:7866/health

# Register user
curl -X POST http://localhost:7866/auth/register `
  -H "Content-Type: application/json" `
  -d '{
    "email": "newuser@example.com",
    "username": "newuser",
    "password": "SecurePassword123"
  }'

# Login
curl -X POST http://localhost:7866/auth/login `
  -H "Content-Type: application/json" `
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePassword123"
  }'

# Copy the "access_token" value from login response, then:
set token=eyJ0eXAiOiJKV1QiLCJhbGc...

# Get user profile (using token)
curl -H "Authorization: Bearer %token%" `
  http://localhost:7866/user/profile

# Check verification status (not verified yet)
curl -H "Authorization: Bearer %token%" `
  http://localhost:7866/verification/status
```

**Expected results:**
- /health returns: `{"status":"healthy"}`
- /auth/register creates user and returns token
- /auth/login returns tokens
- /user/profile returns user details
- /verification/status returns: `{"is_verified":false}`

---

## Phase 9: Git Commit

```bash
# Go to Nudify-Generator directory
cd "C:\working folder\intimai\Nudify-Generator"

# Check what changed
git status

# Add all changes
git add .

# Commit
git commit -m "feat: Integrate user management with age verification

- Add authentication (register/login/JWT)
- Add age verification protection  
- Add credit/quota system
- Add usage tracking
- Protect /v1/engine/generate/ endpoint
- Single unified backend"

# Push to GitHub
git push origin feature/user-management-integration
```

---

## Phase 10: Deploy to RunPod

### Step 1: Push Docker Image

If using Docker:

```bash
# Build
docker build -t nudify-generator:v2.0 .

# Tag (replace 'yourusername')
docker tag nudify-generator:v2.0 yourusername/nudify-generator:v2.0

# Push
docker push yourusername/nudify-generator:v2.0
```

Or use RunPod's GitHub integration to auto-build

### Step 2: Create Pod in RunPod Console

1. Go to https://www.runpod.io/console
2. Click "Deploy"
3. Select GPU template (A40, RTX 3090, etc.)
4. Custom image: `yourusername/nudify-generator:v2.0`
5. Click "Deploy" → Pod starts (2-3 minutes)

### Step 3: Set Environment Variables in Pod

In RunPod pod settings:

```
SUPABASE_URL=https://[your-project-id].supabase.co
SUPABASE_DB_PASSWORD=[your_password]
SUPABASE_KEY=[your_key]
DATABASE_URL=postgresql://postgres:[password]@db.supabase.co:5432/postgres
SECRET_KEY=[your_secret_key]
FOOOCUS_API_PORT=7866
```

### Step 4: Initialize Database in Pod

In RunPod pod terminal:

```bash
python setup_db.py
```

Should show:
```
✓ Environment variables
✓ Database connection
✓ Database tables created
✓ Test user created
```

### Step 5: Test Remote Endpoints

```bash
# Get pod URL from RunPod console
# Should look like: https://[pod-id]-abcd.runpod.io

# Health check
curl https://[pod-id]-abcd.runpod.io/health

# Register
curl -X POST https://[pod-id]-abcd.runpod.io/auth/register `
  -H "Content-Type: application/json" `
  -d '{"email":"test@test.com","username":"test","password":"pass"}'
```

---

## Complete Verification

Once everything is running, verify:

```bash
# Should all return 200 OK

curl http://localhost:7866/health
curl -X POST http://localhost:7866/auth/register -H "Content-Type: application/json" -d '{"email":"t@t.com","username":"t","password":"p"}'
curl -X POST http://localhost:7866/auth/login -H "Content-Type: application/json" -d '{"email":"t@t.com","password":"p"}'
curl -H "Authorization: Bearer <token>" http://localhost:7866/user/profile
curl http://localhost:7866/docs  # Swagger UI
```

---

## Troubleshooting Quick Commands

```bash
# Test imports
python -c "import fastapi; import sqlalchemy; print('OK')"

# Test database
python -c "from database import SessionLocal; db = SessionLocal(); print('DB OK')"

# Test handler loads
python -c "from handler import app; print('Handler OK')"

# Check tables exist
python setup_db.py  # Run again to see what already exists

# Check environment
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('SUPABASE_URL'))"

# See server logs
python handler.py 2>&1 | head -50

# Check what's running on port 7866
netstat -ano | findstr :7866
```

---

## If Something Breaks

### Revert code changes:
```bash
cd C:\working folder\intimai\Nudify-Generator
git checkout handler.py  # Restore original
```

### Recreate database:
```bash
# Drop and recreate (WARNING: Deletes all data)
python -c "
from database import engine
from db_models import Base
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
print('Database recreated')
"
```

### Reinstall dependencies:
```bash
pip uninstall -r requirements_versions.txt -y
pip install -r requirements_versions.txt
```

---

## Summary: What You'll Have After These Steps

✅ **Database** - Supabase PostgreSQL with 4 tables  
✅ **API** - FastAPI with 13 endpoints  
✅ **Auth** - JWT tokens, password hashing  
✅ **Age Verification** - Legal compliance setup  
✅ **Credits** - Usage quotas, tracking  
✅ **Documentation** - 10+ guides  
✅ **Local Testing** - Full dev environment  
✅ **Remote Deployment** - Running on RunPod  

---

## Next Steps After Deployment

1. Create login/register pages in Vue frontend
2. Setup age verification provider (Yoti/Veriff/Persona)
3. Create verification modal in frontend
4. Deploy frontend to Vercel
5. Connect frontend to RunPod API endpoints
6. End-to-end testing

See [COMPLETE_ROADMAP.md](COMPLETE_ROADMAP.md) for detailed Phase 4-6 instructions.

---

**Ready? Start with Phase 1 above! 🚀**
