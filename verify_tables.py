#!/usr/bin/env python3
"""Verify database tables were created"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

sys.path.insert(0, str(Path(__file__).parent))

from database import SessionLocal
from sqlalchemy import text

try:
    db = SessionLocal()
    result = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
    tables = [row[0] for row in result.fetchall()]
    
    print("✓ Tables in database:")
    for table in tables:
        print(f"  - {table}")
    
    print(f"\n✓ Total tables: {len(tables)}")
    
    if len(tables) >= 4:
        print("✓ Database setup successful!")
    else:
        print("⚠️  Expected at least 4 tables")
        
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
