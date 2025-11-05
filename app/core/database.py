"""
Database Connection and Setup
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import os

# Database URL
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
DATABASE_URL = settings.DATABASE_URL or (
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{settings.POSTGRES_DB}"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database (create tables)"""
    Base.metadata.create_all(bind=engine)

