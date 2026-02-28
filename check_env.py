#!/usr/bin/env python3
"""Quick script to verify .env file is loaded correctly"""

from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

print("\n" + "="*60)
print("Environment Variable Check")
print("="*60)

# Key variables to check
checks = [
    ("SAFETY_CHECKER_MODE", "Safety checker mode"),
    ("AWS_REGION", "AWS region"),
    ("AWS_ACCESS_KEY_ID", "AWS access key (first 10 chars)"),
    ("AWS_S3_BUCKET", "S3 bucket name"),
    ("SUPABASE_URL", "Supabase URL"),
    ("DATABASE_URL", "Database URL (first 20 chars)"),
    ("FOOOCUS_API_PORT", "API port"),
    ("DEBUG", "Debug mode"),
]

all_good = True

for key, description in checks:
    value = os.getenv(key)
    if value:
        # Mask sensitive values
        if "KEY" in key or "SECRET" in key or "PASSWORD" in key:
            display_value = value[:10] + "..." if len(value) > 10 else "***"
        elif "URL" in key and len(value) > 30:
            display_value = value[:30] + "..."
        else:
            display_value = value
        
        print(f"✓ {description:30} = {display_value}")
    else:
        print(f"✗ {description:30} = NOT SET")
        all_good = False

print("="*60)

if all_good:
    print("✅ All environment variables loaded successfully!\n")
else:
    print("⚠️  Some variables are missing. Check your .env file.\n")

# Special check for safety mode
mode = os.getenv('SAFETY_CHECKER_MODE', 'strict')
print(f"\n🔧 Active Safety Mode: {mode.upper()}")

if mode == 'permissive_nsfw':
    print("   ⚠️  PERMISSIVE NSFW MODE - Adult content allowed")
else:
    print("   ✓ STRICT MODE - All adult content blocked")

print()
