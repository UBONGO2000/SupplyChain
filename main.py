"""
FastAPI Application - Supply Chain Management API
==================================================
A production-ready REST API for managing supply chain operations.

Features:
- JWT Authentication with role-based access control (RBAC)
- Comprehensive CRUD operations for all entities
- Complex MySQL queries with aggregations, joins, and subqueries
- Input validation and error handling
- API documentation with Swagger UI

Architecture:
- FastAPI for REST endpoints
- SQLAlchemy for ORM
- Pydantic for data validation
- JWT for authentication
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

import models
import database
from auth import get_password_hash
from config import CORS_ORIGINS
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


# ============================================
# Default Users Initialization
# ============================================
def create_default_users():
    """Create default users if they don't exist."""
    db = database.SessionLocal()
    try:
        from models import User

        default_users = [
            {
                "email": "admin@supplychain.com",
                "username": "admin",
                "password": "Admin123!",
                "full_name": "System Administrator",
                "role": "admin",
            },
            {
                "email": "manager@supplychain.com",
                "username": "manager",
                "password": "Manager123!",
                "full_name": "Supply Chain Manager",
                "role": "manager",
            },
            {
                "email": "staff@supplychain.com",
                "username": "staff",
                "password": "Staff123!",
                "full_name": "Warehouse Staff",
                "role": "staff",
            },
            {
                "email": "viewer@supplychain.com",
                "username": "viewer",
                "password": "Viewer123!",
                "full_name": "Viewer User",
                "role": "viewer",
            },
        ]

        for user_data in default_users:
            existing_user = db.query(User).filter(User.username == user_data["username"]).first()
            if not existing_user:
                hashed_password = get_password_hash(user_data["password"])
                new_user = User(
                    email=user_data["email"],
                    username=user_data["username"],
                    hashed_password=hashed_password,
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    is_active=True,
                )
                db.add(new_user)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Warning: Could not create default users: {e}")
    finally:
        db.close()


# ============================================
# Application Lifespan
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    models.Base.metadata.create_all(bind=database.engine)
    create_default_users()
    yield


# ============================================
# Application Initialization
# ============================================
app = FastAPI(
    title="Supply Chain Management API",
    description="Comprehensive API for managing supply chain operations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ============================================
# CORS Middleware
# ============================================
origins = [origin.strip() for origin in CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
# Health Check Endpoint
# ============================================
@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if database.check_database_connection() else "disconnected",
    }


# ============================================
# Run the Application
# ============================================
if __name__ == "__main__":
    import uvicorn
    from config import API_HOST, API_PORT

    uvicorn.run(app, host=API_HOST, port=API_PORT)
