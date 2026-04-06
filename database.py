"""
database.py — Single file that handles all database setup.

Contains:
  - App configuration (loaded from .env)
  - SQLAlchemy engine and session
  - Base class for all models
  - get_db() dependency for FastAPI routes
"""

import os
from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from pydantic_settings import BaseSettings


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    """All app settings. Values are loaded from the .env file."""

    app_name: str = "BankingSystem"
    secret_key: str = "dev-secret-key-please-change-in-production"
    access_token_expire_minutes: int = 60

    database_url: str = "sqlite:///./bank.db"

    # Fraud detection thresholds
    fraud_large_amount: int = 1000000            # flag any transfer above/equal ₹10,00,000
    fraud_rapid_tx_count: int = 5                # flag if more than 5 transactions...
    fraud_rapid_tx_window_minutes: int = 10      # ...happen within 10 minutes

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance — reads .env once and reuses it."""
    return Settings()


# ---------------------------------------------------------------------------
# Database engine and session
# ---------------------------------------------------------------------------

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # needed for SQLite
)

# SessionLocal is a factory — each request gets its own fresh session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Base class for all SQLAlchemy models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """All models inherit from this base class."""
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db():
    """
    Give each HTTP request its own database session,
    and close it automatically when the request finishes.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
