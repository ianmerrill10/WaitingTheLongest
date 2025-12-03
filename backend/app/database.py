"""
===============================================================================
Waiting The Longest™ - Database Configuration
===============================================================================
SQLAlchemy database setup and session management.

Usage:
    from app.database import get_db

    @app.get("/animals")
    def list_animals(db: Session = Depends(get_db)):
        animals = db.query(Animal).all()
        return animals

Author: Waiting The Longest™ Development Team
===============================================================================
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from .config import settings

# Create database engine
# pool_pre_ping=True ensures connections are alive before using
# SQLite doesn't support pool_size/max_overflow, so we conditionally set them
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
        echo=settings.DEBUG
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency for FastAPI routes to get database session.

    Automatically handles:
    - Opening connection
    - Closing connection
    - Rolling back on error

    Usage:
        @app.get("/endpoint")
        def my_endpoint(db: Session = Depends(get_db)):
            # Use db here
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    from . import models  # Import models to register them
    Base.metadata.create_all(bind=engine)
