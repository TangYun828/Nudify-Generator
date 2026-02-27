# Supabase Database Setup Guide

This guide walks you through setting up Supabase for the user management system.

## Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Click "Start your project" or sign in to your account
3. Click "New Project"
4. Fill in:
   - **Name**: `nudify-api` (or your preferred name)
   - **Database Password**: Create a strong password (save it!)
   - **Region**: Choose closest to your users (e.g., `us-east-1`)
5. Click "Create new project" (wait 3-5 minutes for setup)

## Step 2: Get Your Credentials

After project creation, go to **Settings → Database** and copy:

```
Host: db.XXXXX.supabase.co
Port: 5432
Database: postgres
User: postgres
Password: <your-password-from-step-1>
```

Also get from **Settings → API**:
```
Project URL: https://XXXXX.supabase.co
Anon Key: eyJhbGc... (public key)
Service Role Key: eyJhbGc... (secret key - don't share!)
```

## Step 3: Install Required Python Packages

Add these to your `requirements_versions.txt`:

```
psycopg2-binary==2.9.9
PyJWT==2.8.1
passlib==1.7.4
python-multipart==0.0.6
```

Install them:
```bash
pip install psycopg2-binary PyJWT passlib python-multipart
```

## Step 4: Set Environment Variables

### Option A: Local Development (.env file)

Create a `.env` file in the project root:

```env
# Supabase
SUPABASE_URL=https://XXXXX.supabase.co
SUPABASE_KEY=your_service_role_key_here
SUPABASE_DB_PASSWORD=your_database_password

# JWT
SECRET_KEY=your_super_secret_key_change_in_production

# API Configuration
API_PORT=7866
```

**⚠️ Never commit .env to Git!** (.gitignore already includes it)

### Option B: Docker Environment

Add to `docker-compose.yml`:

```yaml
environment:
  SUPABASE_URL: https://XXXXX.supabase.co
  SUPABASE_KEY: your_service_role_key
  SUPABASE_DB_PASSWORD: your_database_password
  SECRET_KEY: your_secret_key
```

### Option C: RunPod Deployment

In RunPod pod settings → Environment:

```
SUPABASE_URL=https://XXXXX.supabase.co
SUPABASE_KEY=your_service_role_key
SUPABASE_DB_PASSWORD=your_password
SECRET_KEY=your_secret_key
```

## Step 5: Initialize the Database

Run this Python command to create all tables:

```python
from database import init_db, test_connection

# Test connection first
test_connection()

# Create all tables
init_db()
```

Or create a setup script `setup_db.py`:

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/content/app')

from database import init_db, test_connection

if __name__ == "__main__":
    print("Testing Supabase connection...")
    if test_connection():
        print("\nInitializing database...")
        if init_db():
            print("\n✓ Database setup complete!")
        else:
            print("\n✗ Database initialization failed")
            sys.exit(1)
    else:
        print("\n✗ Cannot connect to database")
        sys.exit(1)
```

Run it:
```bash
python setup_db.py
```

## Step 6: Verify Database Tables

Log into Supabase console:

1. Go to your Supabase project dashboard
2. Click "SQL Editor" on the left
3. Click "New Query"
4. Run:
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
```

You should see:
- `users`
- `credits`
- `usage_logs`

## Step 7: Test with Sample Data

In Supabase SQL Editor, create a test user:

```sql
INSERT INTO users (id, email, username, password_hash, subscription_tier)
VALUES (
  gen_random_uuid(),
  'test@example.com',
  'testuser',
  '$2b$12$...', -- bcrypt hash (get from running PasswordHandler.hash_password("password"))
  'free'
);
```

Or use Python:
```python
from db_models.user import User
from security import PasswordHandler
from database import SessionLocal

db = SessionLocal()
user = User(
    email="test@example.com",
    username="testuser",
    password_hash=PasswordHandler.hash_password("password123"),
    subscription_tier="free"
)
db.add(user)
db.commit()
print(f"✓ Created user: {user.id}")
db.close()
```

## Troubleshooting

### "Connection refused" error
- Check DATABASE_URL is correct
- Verify Supabase project is running
- Check firewall/IP restrictions in Supabase settings

### "PSYCOPG2 not found" error
```bash
pip install psycopg2-binary
```

### "Schema not found" error
- Run `init_db()` to create tables
- Check you're using correct database (should be "postgres")

### Can't see tables in Supabase console
- Log into Supabase UI → SQL Editor
- Run: `SELECT * FROM information_schema.tables WHERE table_schema = 'public';`
- Tables are there if query returns results

## Next Steps

1. ✅ Database is set up
2. 📝 Create authentication endpoints (register, login)
3. 🔐 Add JWT middleware to FastAPI
4. 💳 Create credit management endpoints
5. 📊 Update handler.py to check user credits

Ready to create the authentication endpoints? 🚀
