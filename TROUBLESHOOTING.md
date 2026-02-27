# Merge & Integration Troubleshooting Guide

## Common Issues & Solutions

### Issue 1: Import Errors After Copy

**Symptom:**
```
ImportError: No module named 'database'
ModuleNotFoundError: No module named 'db_models'
```

**Cause:** Files copied but Python can't find them

**Solution:**
```bash
# Check that files are in correct location
ls database.py
ls -d db_models/

# If missing, copy them again
cp ../nudify-backend/database.py ./
cp -r ../nudify-backend/db_models ./

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Make sure you're in Nudify-Generator root directory
pwd  # Should end with /Nudify-Generator
```

---

### Issue 2: Missing Dependencies

**Symptom:**
```
ModuleNotFoundError: No module named 'fastapi'
ModuleNotFoundError: No module named 'sqlalchemy'
```

**Solution:**
```bash
# Install all requirements
pip install -r requirements_versions.txt

# Or install specific packages:
pip install fastapi uvicorn sqlalchemy psycopg2-binary PyJWT passlib email-validator

# Verify installation
python -c "import fastapi; import sqlalchemy; print('✓ Installed')"
```

---

### Issue 3: Database Connection Failed

**Symptom:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server
```

**Cause:** Missing or incorrect database credentials

**Solution:**

Step 1: Check .env file exists
```bash
cat .env  # Should show SUPABASE_URL, SUPABASE_DB_PASSWORD, etc.
```

Step 2: Verify credentials are correct
```bash
# Test connection manually
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

url = os.getenv('SUPABASE_URL')
password = os.getenv('SUPABASE_DB_PASSWORD')

print(f'URL: {url}')
print(f'Password length: {len(password)}')
print(f'Key env vars loaded: {bool(url and password)}')
"
```

Step 3: If credentials wrong, update .env
```
# .env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_DB_PASSWORD=your_actual_password
SUPABASE_KEY=your_actual_key
DATABASE_URL=postgresql://postgres:password@db.supabase.co:5432/postgres
```

Step 4: Retry
```bash
python setup_db.py
```

---

### Issue 4: handler.py Syntax Errors

**Symptom:**
```
SyntaxError: invalid syntax in handler.py line 152
```

**Solution:**

Step 1: Check the syntax
```bash
python -m py_compile handler.py
```

If it shows line number with error, check that line in editor

Step 2: Common syntax issues:
- Missing colon after function definition: `def handler()` → `def handler():`
- Incorrect indentation (mix of tabs/spaces)
- Unclosed brackets/parentheses
- Missing imports at top

Step 3: Use Python formatter
```bash
# Install formatter
pip install black

# Auto-fix formatting
black handler.py

# Check again
python -m py_compile handler.py
```

Step 4: If still broken, compare with backup
```bash
# See what changed
diff handler.py handler_original_backup.py | head -50

# Restore original and remerge carefully
cp handler_original_backup.py handler.py
```

---

### Issue 5: FastAPI App Not Starting

**Symptom:**
```
ERROR: Application startup failed
```

**Solution:**

Check startup events:
```bash
# See full error
python handler.py 2>&1 | tail -20

# Most likely causes:
# 1. Database connection fails
#    → Check .env credentials

# 2. Missing function
#    → Check init_db() exists in database.py

# 3. Routes not registered
#    → Verify app.include_router() calls exist

# 4. Fooocus startup fails
#    → Make sure FOOOCUS_API_PORT is available
```

Quick debug:
```python
# test_app.py
from handler import app
import asyncio

async def test():
    async with app.lifespan(None) as None:
        print("✓ App startup successful")

asyncio.run(test())
```

---

### Issue 6: /health Endpoint Returns 404

**Symptom:**
```
curl http://localhost:7866/health
404 Not Found
```

**Cause:** Endpoint not registered or wrong port

**Solution:**

Step 1: Check endpoint exists
```bash
# Search in handler.py
grep -n "@app.get" handler.py
grep -n "def health_check" handler.py
```

Should see:
```
@app.get("/health")
async def health_check():
```

Step 2: Check correct port
```bash
# Check what port is running
netstat -an | grep LISTEN  # Windows: netstat -ano | findstr LISTENING

# Default should be 7866
```

Step 3: Verify FastAPI running
```bash
curl http://localhost:7866/docs  # Should work if app running
```

Step 4: Check startup messages
Look for output like:
```
INFO:     Uvicorn running on http://0.0.0.0:7866
```

---

### Issue 7: Registration Returns 500 Error

**Symptom:**
```
POST /auth/register → 500 Internal Server Error
```

**Solution:**

Step 1: Check database tables exist
```bash
python -c "
from database import engine
from db_models import *
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print('Tables:', tables)
"
```

Should show: `['users', 'credits', 'usage_logs', 'age_verifications']`

If missing, run setup:
```bash
python setup_db.py
```

Step 2: Check request body
```bash
curl -X POST http://localhost:7866/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123"
  }'
```

Missing fields will cause 422 error (validation)

Step 3: Check error details
```bash
# Run in debug mode
LOGGING_LEVEL=DEBUG python handler.py

# Then make request and check logs
```

---

### Issue 8: JWT Token Validation Fails

**Symptom:**
```
Bearer eyJ0eXAiOiJKV1QiLCJhbGc... → 403 Unauthorized
```

**Solution:**

Step 1: Check SECRET_KEY set
```bash
python -c "import os; print(f'SECRET_KEY: {os.getenv(\"SECRET_KEY\")}')"
```

Should return actual key, not None

Add to .env if missing:
```
SECRET_KEY=your_super_secret_key_change_in_production
```

Step 2: Verify token format
```bash
# Get token from login
response=$(curl -X POST http://localhost:7866/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }')

token=$(echo $response | jq -r '.access_token')

# Use token
curl -H "Authorization: Bearer $token" \
  http://localhost:7866/user/profile
```

Step 3: Check token expiration
```python
from security import JWTHandler
from datetime import datetime, timedelta

handler = JWTHandler()
token = "eyJ0eXAiOiJKV1QiLCJhbGc..."

try:
    payload = handler.decode_token(token)
    print(f"Token valid until: {datetime.fromtimestamp(payload['exp'])}")
except Exception as e:
    print(f"Token invalid: {e}")
```

---

### Issue 9: Age Verification Status Always 'pending'

**Symptom:**
```
GET /verification/status → {"status": "pending"}
Cannot generate images (403 Forbidden)
```

**Solution:**

Step 1: Check if you've implemented provider callbacks
In `routes/verification.py`, check if webhook handlers are implemented:
```python
# Should have actual implementation
@router.post("/verification/yoti/callback")
async def yoti_callback(data: dict):
    # Should update user.is_verified = True
    # Not just placeholder
```

Step 2: Test with admin endpoint
```bash
curl -X POST http://localhost:7866/verification/admin/verify \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-uuid-here",
    "verified": true
  }'
```

Step 3: Check verification endpoint
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:7866/verification/status
```

Should now return:
```json
{
  "is_verified": true,
  "verified_at": "2024-01-20T10:00:00"
}
```

---

### Issue 10: /docs (Swagger) Not Working

**Symptom:**
```
curl http://localhost:7866/docs → 404 Not Found
```

**Solution:**

This is actually fine. Swagger UI is optional and provided by FastAPI automatically.

If you want it working:

Step 1: Ensure FastAPI initialized correctly
```python
# In handler.py, line should be:
app = FastAPI(title="...", description="...", version="...")

# NOT:
app = FastAPI()  # This works too, just no title
```

Step 2: Verify version of fastapi
```bash
pip show fastapi | grep Version
```

Should be >= 0.95 for Swagger to work

Step 3: Try accessing
```
http://localhost:7866/docs
http://localhost:7866/redoc
http://localhost:7866/openapi.json
```

If openapi.json returns 404, something is wrong with app initialization

---

### Issue 11: RequestException: HTTPSConnectionPool

**Symptom:**
```
HTTPSConnectionPool(host='db.supabase.co', port=5432) failed
```

**Cause:** Cannot reach Supabase server (network or credentials issue)

**Solution:**

Step 1: Check internet connection
```bash
ping 8.8.8.8  # If this fails, no internet
```

Step 2: Verify database URL is correct
```bash
cat .env | grep DATABASE_URL
cat .env | grep SUPABASE_URL

# Should look like:
# SUPABASE_URL=https://xxxxx.supabase.co
# DATABASE_URL=postgresql://postgres:password@db.supabase.co:5432/postgres
```

Step 3: Test connection manually
```bash
# Install postgres client
# Windows: choco install postgresql (with psql)
# Or: https://www.pgadmin.org/

psql "postgresql://postgres:password@db.supabase.co:5432/postgres"
```

If connection fails, check Supabase console:
- Verify project exists
- Check credentials in Project Settings
- Verify IP whitelist (set to 0.0.0.0/0 for testing)

Step 4: For RunPod, use pod's network
If deploying to RunPod:
```bash
# In pod terminal, test connection first
python -c "from sqlalchemy import create_engine; engine = create_engine(os.getenv('DATABASE_URL')); print('✓ Connected')"
```

---

### Issue 12: Credits Not Deducting

**Symptom:**
```
POST /v1/engine/generate/ succeeds
GET /credits/balance shows same credits as before
```

**Solution:**

Step 1: Check Credits table has user record
```python
from database import SessionLocal
from db_models.credits import Credits

db = SessionLocal()
user_credits = db.query(Credits).filter(Credits.user_id == "user_id").first()
print(f"Credits before: {user_credits.credits_remaining if user_credits else 'No record'}")
```

Setup doesn't create credits, must be created with user:
```python
# In auth.py, register endpoint should have:
new_credits = Credits(
    user_id=new_user.id,
    credits_remaining=100.0,  # Free tier
    credits_monthly_limit=100.0,
)
db.add(new_credits)
db.commit()
```

Step 2: Check deduction logic
In handler.py endpoint:
```python
# Must explicitly call:
credits_record.deduct_credits(cost)
db.commit()  # Don't forget this!
```

Step 3: Test manually
```bash
# Get token
token=$(curl -s -X POST http://localhost:7866/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"pass"}' \
  | jq -r '.access_token')

# Check balance before
curl -s -H "Authorization: Bearer $token" \
  http://localhost:7866/credits/balance | jq .

# Generate image
curl -X POST -H "Authorization: Bearer $token" \
  http://localhost:7866/v1/engine/generate/ \
  -d '{"prompt":"test"}' > /dev/null

# Check balance after
curl -s -H "Authorization: Bearer $token" \
  http://localhost:7866/credits/balance | jq .
```

---

### Issue 13: CORS Errors in Frontend

**Symptom:**
```
Access to XMLHttpRequest blocked by CORS policy
```

**Solution:**

Add CORS middleware (should already be in handler.py):

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

For production, replace `["*"]` with specific domains:
```python
allow_origins=[
    "https://yourfrontend.com",
    "https://www.yourfrontend.com",
    "http://localhost:5173"  # Vue dev server
],
```

---

### Issue 14: handler.py Conflicts with Existing Code

**Symptom:**
Fooocus has existing `/v1/engine/generate/` handler, merging creates conflict

**Solution:**

Step 1: Backup both versions
```bash
cp handler.py handler_merged.py
cp handler_original_backup.py handler_original.py
```

Step 2: Find original endpoint
```bash
grep -n "def.*generate" handler_original.py
```

Note the function name and line number

Step 3: Review what original does
```bash
sed -n '150,200p' handler_original.py  # Adjust line numbers
```

Step 4: Merge carefully
The merged handler.py should:
1. Import all dependencies from original
2. Keep original Fooocus functions
3. Wrap the endpoint with auth checks
4. Call original generation logic inside the protected endpoint

See MIGRATION_MERGE_STRATEGY.md "Step 3.2: Structure New handler.py" for exact pattern

Step 5: Test both paths work
```bash
# With token and approval
curl -H "Authorization: Bearer <token>" \
  http://localhost:7866/v1/engine/generate/

# Without token (should fail with 401)
curl http://localhost:7866/v1/engine/generate/
```

---

### General Debugging Commands

```bash
# See full error output
python handler.py 2>&1

# Test imports one by one
python -c "from database import *; print('✓ database')"
python -c "from security import *; print('✓ security')"
python -c "from db_models import *; print('✓ models')"
python -c "from routes import *; print('✓ routes')"
python -c "from handler import app; print('✓ handler')"

# List installed packages
pip list | grep -i fastapi

# Check Python version
python --version

# Look at handler.py structure
grep -n "^def \|^class \|^app\." handler.py | head -30

# See database tables
python -c "from database import engine; from sqlalchemy import inspect; inspector = inspect(engine); print('Tables:', inspector.get_table_names())"

# Test Supabase connection
python -c "from database import SessionLocal; db = SessionLocal(); print('✓ Database OK')"
```

---

## Still Stuck?

1. Check the documentation files:
   - MIGRATION_MERGE_STRATEGY.md (how-to)
   - SUPABASE_SETUP.md (database)
   - AUTHENTICATION_API_COMPLETE.md (API details)

2. Check the error message carefully - the line number usually points to the issue

3. Try simpler version first - can you import files individually?

4. Restore from backup and retry one step at a time

5. If deployed to RunPod and stuck, SSH in and run `python -m pdb handler.py` for interactive debugging
