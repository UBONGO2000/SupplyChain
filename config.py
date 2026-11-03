"""
Centralized Configuration
==========================
Loads all configuration from environment variables.
Never hardcode secrets in source code.

Fail-fast policy: a missing or weak critical setting stops the application
at import time instead of silently falling back to an insecure default.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Database
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Security
# No fallback on purpose: a default secret in the repository would allow
# anyone to forge JWTs for any environment that forgot to set the variable.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise ValueError(
        "SECRET_KEY environment variable is not set or shorter than 32 characters"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# TLS towards MySQL/TiDB. Keep true in production (TiDB Cloud rejects
# unencrypted connections); set DB_SSL=false for a local MySQL.
DB_SSL = _as_bool(os.getenv("DB_SSL", "true"))

# Application
# "test" disables bootstrap/seed side effects at startup.
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
SEED_DEMO_DATA = _as_bool(os.getenv("SEED_DEMO_DATA", "false"))

# Optional first administrator, created only when both values are provided.
BOOTSTRAP_ADMIN_EMAIL = os.getenv("BOOTSTRAP_ADMIN_EMAIL")
BOOTSTRAP_ADMIN_PASSWORD = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
BOOTSTRAP_ADMIN_USERNAME = os.getenv("BOOTSTRAP_ADMIN_USERNAME")

# API
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# CORS - comma-separated list of allowed origins
# Use "*" to allow all origins (not recommended for production)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")

# Optional regex for preview deployments (e.g. "^https://mon-projet-.*\\.vercel\\.app$").
# Empty by default: allowing every *.vercel.app origin would trust any
# attacker-controlled Vercel deployment.
CORS_ORIGIN_REGEX = os.getenv("CORS_ORIGIN_REGEX", "").strip()
