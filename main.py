"""
FastAPI Application - Supply Chain Management API
==================================================
A REST API for managing supply chain operations.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

import database
from auth import get_password_hash
from config import (
    APP_ENV,
    BOOTSTRAP_ADMIN_EMAIL,
    BOOTSTRAP_ADMIN_PASSWORD,
    BOOTSTRAP_ADMIN_USERNAME,
    CORS_ORIGIN_REGEX,
    CORS_ORIGINS,
    SEED_DEMO_DATA,
)
from routers import (
    auth_router,
    warehouses_router,
    suppliers_router,
    products_router,
    inventory_router,
    shipments_router,
    orders_router,
    analytics_router,
)

logger = logging.getLogger("supplychain")

APP_NAME = "Supply Chain Management API"
APP_VERSION = "1.0.0"

DEMO_CREDENTIALS_HINT = (
    "No public demo account is shipped with the repository. Create one with "
    "`python -m cli create-demo-user` (or `docker compose up` for the local "
    "demo) and keep the printed password private."
)


# ============================================
# Bootstrap Administrator (opt-in)
# ============================================
def bootstrap_admin() -> None:
    """Create the first administrator from environment variables.

    There are deliberately no hardcoded accounts anymore: shipping a known
    admin/password pair in the repository gives anyone full access to any
    environment that did not change it. Both BOOTSTRAP_ADMIN_EMAIL and
    BOOTSTRAP_ADMIN_PASSWORD must be provided, and an existing account is
    left untouched so that redeploys never reset a rotated password.
    """
    if not BOOTSTRAP_ADMIN_EMAIL and not BOOTSTRAP_ADMIN_PASSWORD:
        return

    if not BOOTSTRAP_ADMIN_EMAIL or not BOOTSTRAP_ADMIN_PASSWORD:
        raise ValueError(
            "BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD must be set together"
        )

    if len(BOOTSTRAP_ADMIN_PASSWORD) < 12:
        raise ValueError("BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters long")

    from models import User, UserRole

    username = BOOTSTRAP_ADMIN_USERNAME or BOOTSTRAP_ADMIN_EMAIL.split("@")[0]

    db = database.SessionLocal()
    try:
        if db.query(User).filter(User.email == BOOTSTRAP_ADMIN_EMAIL).first():
            print("Bootstrap: administrator already exists, nothing to do.")
            return

        if db.query(User).filter(User.username == username).first():
            raise ValueError(
                f"Bootstrap: username '{username}' is already taken, "
                "set BOOTSTRAP_ADMIN_USERNAME to choose another one"
            )

        db.add(
            User(
                email=BOOTSTRAP_ADMIN_EMAIL,
                username=username,
                hashed_password=get_password_hash(BOOTSTRAP_ADMIN_PASSWORD),
                full_name="Bootstrap Administrator",
                role=UserRole.ADMIN,
                is_active=True,
            )
        )
        db.commit()
        print(f"Bootstrap: administrator '{username}' created.")
    except ValueError:
        db.rollback()
        raise
    except (
        Exception
    ) as exc:  # noqa: BLE001 - startup must not fail on a transient DB error
        db.rollback()
        print(f"Warning: could not create the bootstrap administrator: {exc}")
    finally:
        db.close()


# ============================================
# Application Lifespan
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup events.

    Schema creation/updates are handled by Alembic migrations (run as part
    of the Render build step: `alembic upgrade head`), NOT by create_all()
    anymore. create_all() only creates missing tables and silently ignores
    column changes on existing tables, which caused schema drift in
    production. Alembic replaces it entirely.

    Demo data is opt-in (SEED_DEMO_DATA=true) so that a production database
    never gets sample rows and a failing seed can never prevent the API from
    starting.
    """
    if APP_ENV != "test":
        bootstrap_admin()

        if SEED_DEMO_DATA:
            # The seed is a convenience for demos, never a startup
            # requirement: a database hiccup must not keep the API down.
            try:
                from seed_data import seed_demo_data

                if not seed_demo_data():
                    logger.warning("Demo seed failed; starting the API anyway.")
            except Exception:  # noqa: BLE001 - startup must not depend on the seed
                logger.exception("Demo seed crashed; starting the API anyway.")

    yield


# ============================================
# Application Initialization
# ============================================
app = FastAPI(
    title=APP_NAME,
    description="Comprehensive API for managing supply chain operations",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ============================================
# CORS Middleware
# ============================================
origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # Empty by default: trusting every *.vercel.app origin would let any
    # attacker-owned deployment call the API with credentials.
    allow_origin_regex=CORS_ORIGIN_REGEX or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ============================================
# Include Routers
# ============================================
app.include_router(auth_router)
app.include_router(warehouses_router)
app.include_router(suppliers_router)
app.include_router(products_router)
app.include_router(inventory_router)
app.include_router(shipments_router)
app.include_router(orders_router)
app.include_router(analytics_router)


# ============================================
# Landing Page
# ============================================
@app.get("/", tags=["System"])
def root():
    """Landing page.

    Opening the deployed URL used to return a bare 404, which looks like a
    broken deployment. A JSON index makes the service self-describing.
    """
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "demo_credentials_hint": DEMO_CREDENTIALS_HINT,
    }


# ============================================
# Health Check Endpoint
# ============================================
@app.get("/health", tags=["Health"])
def health_check(response: Response):
    """Health check endpoint.

    Returns 503 when the database is unreachable, so uptime monitors and
    orchestrators see an actual failure instead of a green status forever.
    """
    db_connected = database.check_database_connection()
    response.status_code = 200 if db_connected else 503

    return {
        "status": "healthy" if db_connected else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "connected" if db_connected else "disconnected",
    }
