"""
Database configuration and session management for tenant system.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database URL - can be configured via environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tenant_system.db")

# Create engine with proper connection pooling
if "sqlite" in DATABASE_URL:
    # SQLite configuration
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False  # Set to True for SQL query logging
    )
else:
    # PostgreSQL/Supabase configuration with connection pooling
    # Using smaller pool size to avoid hitting Supabase connection limits
    engine = create_engine(
        DATABASE_URL,
        pool_size=2,  # Maximum number of permanent connections (reduced for Supabase free tier)
        max_overflow=3,  # Maximum number of temporary connections
        pool_timeout=30,  # Timeout for getting a connection from pool
        pool_recycle=300,  # Recycle connections after 5 minutes (important for pgbouncer)
        pool_pre_ping=True,  # Verify connections before using them
        echo=False  # Set to True for SQL query logging
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    Use with FastAPI Depends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables.
    Call this on application startup.
    """
    Base.metadata.create_all(bind=engine)
