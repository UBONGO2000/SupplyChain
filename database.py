"""
Database Configuration Module
==============================
Handles database connection with SQLAlchemy including:
- Connection pooling
- Environment-based configuration
- Session management
- Security best practices
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
from typing import Generator

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")


# ============================================
# Engine Configuration with Connection Pooling
# ============================================
# Using QueuePool for connection pooling in multi-threaded environments
# - pool_size: Number of connections to keep open
# - max_overflow: Additional connections allowed when pool is full
# - pool_pre_ping: Verify connection validity before using
# - pool_recycle: Recycle connections after this many seconds

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,  # Set to True for SQL debugging
    connect_args={
        "charset": "utf8mb4"
    }
)


# ============================================
# Enable foreign key constraints for MySQL
# ============================================
@event.listens_for(engine, "connect")
def set_sql_mode(dbapi_connection, connection_record):
    """
    Set MySQL session variables for proper foreign key support
    and strict SQL mode for data integrity.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("SET SESSION sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'")
    cursor.close()


# ============================================
# Session Factory
# ============================================
# autocommit=False: Transactions must be explicitly committed
# autoflush=False: Changes are only sent to DB when flush() is called
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Prevent lazy loading issues after commit
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
    
    Yields:
        Session: SQLAlchemy session instance
    
    Ensures:
        - Session is properly closed after request
        - Transaction is rolled back on exception
    
    Usage in FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
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
# Database Initialization Function
# ============================================
def init_db() -> None:
    """
    Initialize database tables.
    Creates all tables defined in models that inherit from Base.
    
    Note: In production, use Alembic migrations instead.
    """
    Base.metadata.create_all(bind=engine)


# ============================================
# Utility Functions
# ============================================
def check_database_connection() -> bool:
    """
    Verify database connectivity.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            return True
    except Exception:
        return False


def get_database_url() -> str:
    """
    Get the current database URL (masked for security).
    
    Returns:
        str: Masked database URL
    """
    if "@" in DATABASE_URL:
        # Mask credentials
        parts = DATABASE_URL.split("@")
        return f"{parts[0].split(':')[0]}:****@{parts[1]}"
    return DATABASE_URL
