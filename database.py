"""
Database Configuration Module
==============================
Handles database connection with SQLAlchemy including:
- Connection pooling
- Environment-based configuration
- Session management
- Security best practices
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool
from typing import Generator

import ssl

from config import DATABASE_URL


# ============================================
# SSL for TiDB Cloud (requires secure transport)
# ============================================
ssl_context = ssl.create_default_context()


# ============================================
# Engine Configuration with Connection Pooling
# ============================================
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
    connect_args={
        "charset": "utf8mb4",
        "ssl": ssl_context,
    },
)


# ============================================
# Enable strict SQL mode for MySQL
# ============================================
@event.listens_for(engine, "connect")
def set_sql_mode(dbapi_connection, connection_record):
    """
    Set MySQL session variables for proper foreign key support
    and strict SQL mode for data integrity.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute(
        "SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,"
        "ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'"
    )
    cursor.close()


# ============================================
# Session Factory
# ============================================
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


# ============================================
# Base Class for ORM Models
# ============================================
Base = declarative_base()


# ============================================
# Database Dependency for FastAPI
# ============================================
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.
    Ensures session is properly closed and transactions are rolled back on error.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ============================================
# Utility Functions
# ============================================
def init_db() -> None:
    """Initialize database tables. In production, use Alembic migrations instead."""
    Base.metadata.create_all(bind=engine)


def check_database_connection() -> bool:
    """Verify database connectivity."""
    try:
        with engine.connect():
            return True
    except Exception:
        return False
