"""
Supabase Database Configuration
Manages PostgreSQL connection via Supabase
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# Get Supabase connection details from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # Service role key
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD")

# Build PostgreSQL connection string
# Format: postgresql://user:password@host:port/database
if SUPABASE_DB_PASSWORD and SUPABASE_URL:
    # Use Supabase connection pooler (Session mode)
    project_id = SUPABASE_URL.split('https://')[1].split('.supabase.co')[0]
    DATABASE_URL = (
        f"postgresql://postgres.{project_id}:{SUPABASE_DB_PASSWORD}@"
        f"aws-0-us-west-2.pooler.supabase.com:5432/postgres"
    )
else:
    # Fallback - use DATABASE_URL from environment
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost/nudify"
    )

# SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,  # Test connections before using
    pool_recycle=3600,  # Recycle connections every hour
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def get_db():
    """Dependency to get database session in FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - creates all tables"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Database initialized - all tables created")
        return True
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False


def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Database connection successful")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
