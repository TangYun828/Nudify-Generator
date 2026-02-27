#!/usr/bin/env python3
"""
Database Initialization Script
Run this script to set up the Supabase database and create all tables
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database import init_db, test_connection, SessionLocal
from db_models.user import User
from db_models.credits import Credits
from security import PasswordHandler, APIKeyHandler


def check_environment():
    """Check if required environment variables are set"""
    print("=" * 60)
    print("Checking environment variables...")
    print("=" * 60)
    
    required = ["SUPABASE_URL", "SUPABASE_DB_PASSWORD", "SECRET_KEY"]
    missing = []
    
    for var in required:
        value = os.getenv(var)
        if value:
            # Hide sensitive values
            display = f"{value[:10]}..." if len(value) > 10 else value
            print(f"✓ {var}: {display}")
        else:
            print(f"✗ {var}: NOT SET")
            missing.append(var)
    
    if missing:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing)}")
        print("\nPlease set them in .env or as environment variables:")
        print("  export SUPABASE_URL=https://xxxxx.supabase.co")
        print("  export SUPABASE_DB_PASSWORD=your_password")
        print("  export SECRET_KEY=your_secret_key")
        return False
    
    print("\n✓ All environment variables are set\n")
    return True


def test_database_connection():
    """Test connection to database"""
    print("=" * 60)
    print("Testing database connection...")
    print("=" * 60)
    
    if test_connection():
        return True
    else:
        print("\n✗ Database connection failed")
        print("Please check:")
        print("  1. Supabase project is running")
        print("  2. DATABASE_URL is correct")
        print("  3. Network connection is available")
        return False


def initialize_database():
    """Create all database tables"""
    print("\n" + "=" * 60)
    print("Initializing database...")
    print("=" * 60)
    
    try:
        init_db()
        return True
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False


def create_test_user():
    """Create a test user for development"""
    print("\n" + "=" * 60)
    print("Creating test user...")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Check if test user already exists
        existing = db.query(User).filter(User.email == "test@example.com").first()
        if existing:
            print("✓ Test user already exists (test@example.com)")
            db.close()
            return True
        
        # Create test user
        test_user = User(
            email="test@example.com",
            username="testuser",
            password_hash=PasswordHandler.hash_password("password123"),
            api_key=APIKeyHandler.generate_api_key(),
            subscription_tier="free"
        )
        
        db.add(test_user)
        db.flush()
        
        # Create credits for test user
        test_credits = Credits(
            user_id=test_user.id,
            credits_remaining=10.0,
            credits_monthly_limit=10.0,
            subscription_tier="free"
        )
        
        db.add(test_credits)
        db.commit()
        
        print(f"✓ Test user created successfully")
        print(f"  Email: test@example.com")
        print(f"  Password: password123")
        print(f"  API Key: {test_user.api_key}")
        print(f"  Credits: 10.0")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ Failed to create test user: {e}")
        db.close()
        return False


def show_summary():
    """Show setup summary"""
    print("\n" + "=" * 60)
    print("Database Setup Complete! ✓")
    print("=" * 60)
    
    print("\nNext steps:")
    print("1. Create .env file with environment variables")
    print("2. Install dependencies: pip install -r requirements_versions.txt")
    print("3. Start the API server:")
    print("   python handler.py  (or use launch.py)")
    
    print("\nTest the API:")
    print("  POST /auth/register - Create new user")
    print("  POST /auth/login - Login with email/password")
    print("  GET /user/profile - Get user profile (requires token)")
    print("  GET /credits/balance - Get credit balance")
    
    print("\nTest user credentials:")
    print("  Email: test@example.com")
    print("  Password: password123")
    
    print("\nDocumentation:")
    print("  http://localhost:7866/docs - Swagger UI")
    print("  http://localhost:7866/redoc - ReDoc")


def main():
    """Main setup flow"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " Nudify Database Setup Script ".center(58) + "║")
    print("╚" + "=" * 58 + "╝\n")
    
    # Step 1: Check environment
    if not check_environment():
        sys.exit(1)
    
    # Step 2: Test connection
    if not test_database_connection():
        sys.exit(1)
    
    # Step 3: Initialize database
    if not initialize_database():
        sys.exit(1)
    
    # Step 4: Create test user
    create_test_user()
    
    # Step 5: Show summary
    show_summary()
    
    print("\n✓ Setup complete!\n")


if __name__ == "__main__":
    main()
