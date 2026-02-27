# Integration Guide: Nudify User Management + Fooocus

## Overview

The integrated handler combines:
- **Fooocus**: Image generation (existing functionality)
- **FastAPI**: REST API with user endpoints
- **PostgreSQL**: User accounts, credits, usage tracking
- **JWT Authentication**: Secure token-based auth

## File Structure

```
Nudify-Generator/
├── handler_integrated.py      # NEW: Combined FastAPI + RunPod handler
├── handler.py                 # ORIGINAL: RunPod serverless handler (backup)
├── database.py                # COPIED: Supabase PostgreSQL config
├── security.py                # COPIED: Auth, tokens, password hashing
├── schemas.py                 # COPIED: Pydantic request/response models
├── db_models/                 # COPIED: SQLAlchemy models
│   ├── __init__.py
│   ├── user.py
│   ├── credits.py
│   └── usage_log.py
└── .env                       # COPIED: Supabase credentials
```

## Setup

### 1. Copy Files (Already Done)
- User management code from `nudify-backend/` copied to `Nudify-Generator/`
- Environment variables (`.env`) configured with Supabase credentials

### 2. Install Dependencies

Add to `requirements_versions.txt`:
```
fastapi==0.109.0
uvicorn==0.28.0
python-dotenv==1.0.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.11
PyJWT==2.8.1
passlib==1.7.4
bcrypt==4.1.1
email-validator==2.0.0
```

### 3. Environment Configuration

The `.env` file already configured:
```
SUPABASE_URL=https://fldcxpaudayylsirlghs.supabase.co
SUPABASE_DB_PASSWORD=WfxfQ9ng7DTJHeuV
SUPABASE_SERVICE_ROLE_KEY=[JWT token]
SECRET_KEY=nudify_secret_key_change_this_in_production_8x7y9z2w3q4r5t6u
DATABASE_URL=postgresql://postgres.fldcxpaudayylsirlghs:***@aws-0-us-west-2.pooler.supabase.com:5432/postgres
FOOOCUS_API_PORT=7866
DEBUG=False
```

## Running

### Local Testing (FastAPI)
```bash
cd Nudify-Generator
python handler_integrated.py
```

Starts:
- Fooocus API on `http://127.0.0.1:7866`
- FastAPI on `http://localhost:8000`
- Visit `http://localhost:8000/docs` for interactive API documentation

### Production (RunPod)
```bash
python handler_integrated.py
```

When installed on RunPod with `runpod` SDK available:
- Automatically runs in serverless mode
- Exports `handler()` function for RunPod
- Uses same codebase as local

## API Endpoints

### Authentication

**Register User**
```bash
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "username",
  "password": "password123"
}

Response:
{
  "message": "User registered successfully",
  "user_id": "uuid"
}
```

**Login**
```bash
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user_id": "uuid"
}
```

### User Profile

**Get Profile**
```bash
GET /user/profile
Authorization: Bearer <token>

Response:
{
  "user_id": "uuid",
  "email": "user@example.com",
  "username": "username",
  "credits": 10,
  "created_at": "2026-02-26T00:00:00"
}
```

### Image Generation

**Generate Image(s)**
```bash
POST /generate/image
Authorization: Bearer <token>
Content-Type: application/json

{
  "prompt": "A beautiful portrait of a woman",
  "negative_prompt": "low quality, blurry",
  "image_number": 1,
  "base_model_name": "onlyfornsfw118_v20.safetensors",
  "aspect_ratio": "1024*1024",
  "output_format": "png"
}

Response:
{
  "images": ["base64_encoded_image"],
  "credits_used": 1,
  "credits_remaining": 9,
  "message": "Generated 1 image(s)"
}
```

**Get Credit Balance**
```bash
GET /credits/balance
Authorization: Bearer <token>

Response:
{
  "balance": 9,
  "total_earned": 10,
  "total_spent": 1
}
```

## Credit System

**Default Values:**
- Free credits on signup: 10
- Cost per image: 1 credit
- Users must have sufficient credits before generation

**Credit Deduction Flow:**
1. User requests image generation
2. System checks user has enough credits
3. Request sent to Fooocus API
4. On success: Credits deducted, usage logged
5. On failure: No credits deducted, error logged

## Database Schema

### Users Table
```sql
- id (UUID PRIMARY KEY)
- email (VARCHAR UNIQUE)
- username (VARCHAR)
- hashed_password (VARCHAR)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

### Credits Table
```sql
- id (UUID PRIMARY KEY)
- user_id (UUID FK -> users)
- balance (DECIMAL)
- total_earned (DECIMAL)
- total_spent (DECIMAL)
- updated_at (TIMESTAMP)
```

### Usage Logs Table
```sql
- id (UUID PRIMARY KEY)
- user_id (UUID FK -> users)
- endpoint (VARCHAR)
- method (VARCHAR)
- prompt (TEXT)
- credits_deducted (DECIMAL)
- status (VARCHAR)
- request_metadata (JSON)
- created_at (TIMESTAMP)
- completed_at (TIMESTAMP)
```

## RunPod Serverless Handler

The `handler()` function supports both:

**1. FastAPI Routes** (REST API)
```
POST /auth/register
POST /auth/login
GET /user/profile
POST /generate/image
GET /credits/balance
```

**2. RunPod Event Format** (backward compatible)
```json
{
  "input": {
    "prompt": "A beautiful portrait",
    "image_number": 1,
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "base_model_name": "onlyfornsfw118_v20.safetensors",
    "negative_prompt": "low quality",
    "aspect_ratio": "1024*1024",
    "output_format": "png"
  }
}
```

## Testing Workflow

### 1. Register
```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123"
  }'
```

### 2. Login
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
# Copy the token from response
```

### 3. Generate Image
```bash
curl -X POST "http://localhost:8000/generate/image" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset",
    "image_number": 1
  }'
```

### 4. Check Balance
```bash
curl -X GET "http://localhost:8000/credits/balance" \
  -H "Authorization: Bearer <TOKEN>"
```

## Troubleshooting

### Database Connection Failed
- Check `.env` has correct `SUPABASE_DB_PASSWORD`
- Verify connection string in `DATABASE_URL`
- Ensure Windows hosts file has `52.8.172.168 db.fldcxpaudayylsirlghs.supabase.co`

### Fooocus API Not Ready
- Allow 60+ seconds for model loading on first startup
- Check logs for model download status
- Ensure sufficient disk space for models

### Credit Deduction Not Working
- Verify user has credits with GET `/credits/balance`
- Check DATABASE_URL and user table exists
- Review usage_logs table for error entries

## Migration from Original Handler

The original `handler.py` is preserved. To switch:

**Use integrated version (recommended):**
```bash
# In index.json or deployment config
"handler": "handler_integrated.handler"
```

**Use original version (if needed):**
```bash
"handler": "handler.handler"
```

## Next Steps

1. Deploy to RunPod serverless
2. Configure custom domain
3. Set up age verification provider integration
4. Implement admin dashboard for analytics
5. Add credit purchase system (optional)

## Support

For issues:
1. Check logs: `docker logs <container_id>`
2. Review DATABASE_URL in console output
3. Verify JWT tokens: https://jwt.io
4. Test Fooocus directly at `http://localhost:7866/docs`
5. Check Supabase dashboard for table data
