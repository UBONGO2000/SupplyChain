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

Security:
- Password hashing with bcrypt
- JWT tokens with expiration
- Role-based access control (ADMIN, MANAGER, STAFF, VIEWER)
- Input sanitization and validation
"""

from fastapi import FastAPI, HTTPException, status, Depends, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import math

import models
import database
import schema
from schema import (
    UserCreate, UserResponse, UserUpdate, UserLogin, TokenResponse,
    WarehouseCreate, WarehouseResponse, WarehouseUpdate,
    SupplierCreate, SupplierResponse, SupplierUpdate,
    ProductCreate, ProductResponse, ProductUpdate, ProductWithInventoryResponse,
    InventoryResponse, InventoryCreate, InventoryUpdate, InventoryAdjustRequest,
    ShipmentCreate, ShipmentResponse, ShipmentUpdate,
    OrderCreate, OrderResponse, OrderUpdate,
    PaginatedResponse, MessageResponse, PaginationParams,
    InventorySummary, SalesSummary, LowStockAlert
)

from auth import (
    get_password_hash, verify_password, create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user, require_role
)


# ============================================
# Application Initialization
# ============================================
app = FastAPI(
    title="Supply Chain Management API",
    description="Comprehensive API for managing supply chain operations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Create database tables on startup
models.Base.metadata.create_all(bind=database.engine)


# ============================================
# Default Users Initialization
# ============================================
def create_default_users():
    """Create default users if they don't exist."""
    from models import User
    from auth import get_password_hash
    
    db = next(database.get_db())
    
    default_users = [
        {
            "email": "admin@supplychain.com",
            "username": "admin",
            "password": "Admin123!",
            "full_name": "System Administrator",
            "role": "admin"
        },
        {
            "email": "manager@supplychain.com",
            "username": "manager",
            "password": "Manager123!",
            "full_name": "Supply Chain Manager",
            "role": "manager"
        },
        {
            "email": "staff@supplychain.com",
            "username": "staff",
            "password": "Staff123!",
            "full_name": "Warehouse Staff",
            "role": "staff"
        },
        {
            "email": "viewer@supplychain.com",
            "username": "viewer",
            "password": "Viewer123!",
            "full_name": "Viewer User",
            "role": "viewer"
        }
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
                is_active=True
            )
            db.add(new_user)
    
    db.commit()


# Create default users on startup
create_default_users()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ============================================
# Dependency for Database Session
# ============================================
# Using get_db from database module (defined in database.py)
# This avoids duplication and ensures consistent typing
get_db = database.get_db


# ============================================
# Health Check Endpoint
# ============================================
@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if database.check_database_connection() else "disconnected"
    }


# ============================================
# AUTHENTICATION ROUTES
# ============================================
@app.post("/api/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.
    
    - **email**: Valid email address (unique)
    - **username**: Unique username (3-100 chars)
    - **password**: Password (min 8 chars, must contain uppercase, lowercase, digit)
    - **full_name**: Optional full name
    - **role**: User role (admin, manager, staff, viewer)
    """
    # Check if email already exists
    existing_email = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    existing_username = db.query(models.User).filter(models.User.username == user.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Hash password and create user
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role.value,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@app.post("/api/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.
    
    Use form data with:
    - **username**: Username or email
    - **password**: User password
    """
    # Try to find user by username or email
    user = db.query(models.User).filter(
        or_(
            models.User.username == form_data.username,
            models.User.email == form_data.username
        )
    ).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role.value}
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user
    )


@app.get("/api/auth/me", response_model=UserResponse, tags=["Authentication"])
def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    """Get current authenticated user information"""
    return current_user


# ============================================
# WAREHOUSE ROUTES (CRUD + Complex Queries)
# ============================================
@app.post("/api/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED, tags=["Warehouses"])
def create_warehouse(
    warehouse: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"]))
):
    """Create a new warehouse (Admin/Manager only)"""
    db_warehouse = models.Warehouse(**warehouse.model_dump())
    db.add(db_warehouse)
    db.commit()
    db.refresh(db_warehouse)
    return db_warehouse


@app.get("/api/warehouses", response_model=PaginatedResponse, tags=["Warehouses"])
def get_warehouses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all warehouses with pagination and filtering.
    
    - **page**: Page number (starts at 1)
    - **page_size**: Items per page (max 100)
    - **search**: Search by name or location
    - **is_active**: Filter by active status
    """
    query = db.query(models.Warehouse)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                models.Warehouse.name.ilike(f"%{search}%"),
                models.Warehouse.location.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.filter(models.Warehouse.is_active == is_active)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginatedResponse.create(items, total, page, page_size)


@app.get("/api/warehouses/{warehouse_id}", response_model=WarehouseResponse, tags=["Warehouses"])
def get_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get warehouse by ID"""
    warehouse = db.query(models.Warehouse).filter(models.Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return warehouse


@app.put("/api/warehouses/{warehouse_id}", response_model=WarehouseResponse, tags=["Warehouses"])
def update_warehouse(
    warehouse_id: int,
    warehouse: WarehouseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"]))
):
    """Update warehouse (Admin/Manager only)"""
    db_warehouse = db.query(models.Warehouse).filter(models.Warehouse.id == warehouse_id).first()
    if not db_warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Update only provided fields
    update_data = warehouse.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_warehouse, key, value)
    
    db.commit()
    db.refresh(db_warehouse)
    return db_warehouse


@app.delete("/api/warehouses/{warehouse_id}", response_model=MessageResponse, tags=["Warehouses"])
def delete_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin"]))
):
    """Delete warehouse (Admin only)"""
    warehouse = db.query(models.Warehouse).filter(models.Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Check if warehouse has inventory
    inventory_count = db.query(models.Inventory).filter(models.Inventory.warehouse_id == warehouse_id).count()
    if inventory_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete warehouse with existing inventory. Transfer inventory first."
        )
    
    db.delete(warehouse)
    db.commit()
    return MessageResponse(message="Warehouse deleted successfully")


# ============================================
# SUPPLIER ROUTES (CRUD + Complex Queries)
# ============================================
@app.post("/api/suppliers", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED, tags=["Suppliers"])
def create_supplier(
    supplier: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"]))
):
    """Create a new supplier (Admin/Manager only)"""
    db_supplier = models.Supplier(**supplier.model_dump())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


@app.get("/api/suppliers", response_model=PaginatedResponse, tags=["Suppliers"])
def get_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    country: Optional[str] = None,
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all suppliers with advanced filtering.
    
    - **page**: Page number
    - **page_size**: Items per page
    - **search**: Search by company name
    - **country**: Filter by country
    - **min_rating**: Minimum rating filter
    """
    query = db.query(models.Supplier)
    
    if search:
        query = query.filter(models.Supplier.company_name.ilike(f"%{search}%"))
    
    if country:
        query = query.filter(models.Supplier.country == country)
    
    if min_rating is not None:
        query = query.filter(models.Supplier.rating >= min_rating)
    
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginatedResponse.create(items, total, page, page_size)


@app.get("/api/suppliers/{supplier_id}", response_model=SupplierResponse, tags=["Suppliers"])
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get supplier by ID with product count"""
    supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@app.put("/api/suppliers/{supplier_id}", response_model=SupplierResponse, tags=["Suppliers"])
def update_supplier(
    supplier_id: int,
    supplier: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"]))
):
    """Update supplier (Admin/Manager only)"""
    db_supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    update_data = supplier.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_supplier, key, value)
    
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


# ============================================
# PRODUCT ROUTES (CRUD + Complex Queries)
# ============================================
@app.post("/api/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, tags=["Products"])
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"]))
):
    """Create a new product (Admin/Manager only)"""
    # Check for duplicate SKU
    existing = db.query(models.Product).filter(models.Product.sku == product.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@app.get("/api/products", response_model=PaginatedResponse, tags=["Products"])
def get_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[schema.ProductCategoryEnum] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    supplier_id: Optional[int] = None,
    low_stock_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all products with advanced filtering and search.
    
    - **search**: Search by name or SKU
    - **category**: Filter by category
    - **min_price/max_price**: Price range filter
    - **supplier_id**: Filter by supplier
    - **low_stock_only**: Show only products below reorder point
    """
    query = db.query(models.Product)
    
    if search:
        query = query.filter(
            or_(
                models.Product.name.ilike(f"%{search}%"),
                models.Product.sku.ilike(f"%{search}%")
            )
        )
    
    if category:
        query = query.filter(models.Product.category == category.value)
    
    if min_price is not None:
        query = query.filter(models.Product.unit_price >= min_price)
    
    if max_price is not None:
        query = query.filter(models.Product.unit_price <= max_price)
    
    if supplier_id:
        query = query.filter(models.Product.supplier_id == supplier_id)
    
    # Get total before low_stock filter
    total = query.count()
    
    # Apply pagination
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginatedResponse.create(items, total, page, page_size)


@app.get("/api/products/{product_id}", response_model=ProductWithInventoryResponse, tags=["Products"])
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get product by ID with inventory summary"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get inventory summary using aggregation
    inventory_summary = db.query(
        func.count(models.Inventory.product_id).label("warehouses_count"),
        func.sum(models.Inventory.quantity).label("total_quantity"),
        func.sum(models.Inventory.available_quantity).label("available_quantity")
    ).filter(models.Inventory.product_id == product_id).first()
    
    response = ProductWithInventoryResponse(
        **product.__dict__,
        total_quantity=inventory_summary.total_quantity or 0,
        available_quantity=inventory_summary.available_quantity or 0,
        warehouses_count=inventory_summary.warehouses_count or 0
    )
    return response


@app.put("/api/products/{product_id}", response_model=ProductResponse, tags=["Products"])
def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"]))
):
    """Update product (Admin/Manager only)"""
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
    
    db.commit()
    db.refresh(db_product)
    return db_product


# ============================================
# INVENTORY ROUTES (CRUD + Complex Queries)
# ============================================
@app.post("/api/inventory", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED, tags=["Inventory"])
def create_inventory(
    inventory: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager", "staff"]))
):
    """Create inventory record (Admin/Manager/Staff)"""
    # Check if record already exists
    existing = db.query(models.Inventory).filter(
        and_(
            models.Inventory.warehouse_id == inventory.warehouse_id,
            models.Inventory.product_id == inventory.product_id
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Inventory record already exists for this warehouse-product combination"
        )
    
    # Validate warehouse exists
    warehouse = db.query(models.Warehouse).filter(models.Warehouse.id == inventory.warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    
    # Validate product exists
    product = db.query(models.Product).filter(models.Product.id == inventory.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Calculate available quantity
    available = inventory.quantity - (inventory.reserved_quantity or 0)
    
    db_inventory = models.Inventory(
        **inventory.model_dump(),
        available_quantity=available
    )
    db.add(db_inventory)
    db.commit()
    db.refresh(db_inventory)
    return db_inventory


@app.get("/api/inventory", response_model=PaginatedResponse, tags=["Inventory"])
def get_inventory(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    warehouse_id: Optional[int] = None,
    product_id: Optional[int] = None,
    low_stock: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get inventory with filtering.
    
    - **warehouse_id**: Filter by warehouse
    - **product_id**: Filter by product
    - **low_stock**: Show only items below reorder level
    """
    query = db.query(models.Inventory).options(
        joinedload(models.Inventory.warehouse),
        joinedload(models.Inventory.product)
    )
    
    if warehouse_id:
        query = query.filter(models.Inventory.warehouse_id == warehouse_id)
    
    if product_id:
        query = query.filter(models.Inventory.product_id == product_id)
    
    if low_stock:
        query = query.filter(models.Inventory.quantity < models.Inventory.reorder_level)
    
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginatedResponse.create(items, total, page, page_size)


@app.get("/api/inventory/warehouse/{warehouse_id}", response_model=PaginatedResponse, tags=["Inventory"])
def get_warehouse_inventory(
    warehouse_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all inventory for a specific warehouse with pagination"""
    query = db.query(models.Inventory).options(
        joinedload(models.Inventory.product)
    ).filter(models.Inventory.warehouse_id == warehouse_id)
    
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginatedResponse.create(items, total, page, page_size)


@app.post("/api/inventory/adjust", response_model=InventoryResponse, tags=["Inventory"])
def adjust_inventory(
    warehouse_id: int,
    product_id: int,
    adjustment: InventoryAdjustRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager", "staff"]))
):
    """
    Adjust inventory quantity (add or remove stock).
    
    - **adjustment**: Positive to add, negative to remove
    - **reason**: Optional reason for the adjustment
    """
    inventory = db.query(models.Inventory).filter(
        and_(
            models.Inventory.warehouse_id == warehouse_id,
            models.Inventory.product_id == product_id
        )
    ).first()
    
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory record not found")
    
    new_quantity = inventory.quantity + adjustment.adjustment
    
    if new_quantity < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Current: {inventory.quantity}, Requested adjustment: {adjustment.adjustment}"
        )
    
    inventory.quantity = new_quantity
    inventory.available_quantity = new_quantity - inventory.reserved_quantity
    
    db.commit()
    db.refresh(inventory)
    return inventory


# ============================================
# SHIPMENT ROUTES (CRUD + Complex Queries)
# ============================================
@app.post("/api/shipments", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED, tags=["Shipments"])
def create_shipment(
    shipment: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager", "staff"]))
):
    """Create a new shipment"""
    db_shipment = models.Shipment(**shipment.model_dump())
    db.add(db_shipment)
    db.commit()
    db.refresh(db_shipment)
    return db_shipment


@app.get("/api/shipments", response_model=PaginatedResponse, tags=["Shipments"])
def get_shipments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[schema.ShipmentStatusEnum] = None,
    supplier_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all shipments with filtering"""
    query = db.query(models.Shipment)
    
    if status:
        query = query.filter(models.Shipment.status == status.value)
    
    if supplier_id:
        query = query.filter(models.Shipment.supplier_id == supplier_id)
    
    if warehouse_id:
        query = query.filter(models.Shipment.origin_warehouse_id == warehouse_id)
    
    total = query.count()
    items = query.order_by(desc(models.Shipment.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginatedResponse.create(items, total, page, page_size)


@app.get("/api/shipments/{shipment_id}", response_model=ShipmentResponse, tags=["Shipments"])
def get_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get shipment by ID"""
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


@app.put("/api/shipments/{shipment_id}", response_model=ShipmentResponse, tags=["Shipments"])
def update_shipment(
    shipment_id: int,
    shipment: ShipmentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager", "staff"]))
):
    """Update shipment status"""
    db_shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not db_shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    update_data = shipment.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_shipment, key, value)
    
    db.commit()
    db.refresh(db_shipment)
    return db_shipment


# ============================================
# ORDER ROUTES (CRUD + Complex Queries)
# ============================================
@app.post("/api/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, tags=["Orders"])
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new order with items"""
    # Validate user exists
    user = db.query(models.User).filter(models.User.id == order.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate order totals
    subtotal = Decimal("0.00")
    order_items_data = []
    
    for item in order.items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        
        # Calculate line total with discount
        discount_amount = item.unit_price * (item.discount_percent / 100)
        line_total = (item.unit_price - discount_amount) * item.quantity
        subtotal += line_total
        
        order_items_data.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "discount_percent": item.discount_percent,
            "line_total": line_total
        })
    
    # Calculate tax and total
    tax_rate = Decimal("0.20")  # 20% tax
    tax_amount = subtotal * tax_rate
    shipping_cost = Decimal("10.00") if subtotal < Decimal("100.00") else Decimal("0.00")
    total_amount = subtotal + tax_amount + shipping_cost
    
    # Generate order number
    order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{int(datetime.utcnow().timestamp())}"
    
    # Create order
    db_order = models.Order(
        order_number=order_number,
        user_id=order.user_id,
        shipping_address=order.shipping_address,
        billing_address=order.billing_address,
        notes=order.notes,
        subtotal=subtotal,
        tax_amount=tax_amount,
        shipping_cost=shipping_cost,
        total_amount=total_amount,
        status=models.OrderStatus.PENDING
    )
    db.add(db_order)
    db.flush()  # Get the order ID
    
    # Create order items
    for item_data in order_items_data:
        order_item = models.OrderItem(order_id=db_order.id, **item_data)
        db.add(order_item)
        
        # Reserve inventory
        inventory = db.query(models.Inventory).filter(
            and_(
                models.Inventory.product_id == item_data["product_id"],
                models.Inventory.available_quantity >= item_data["quantity"]
            )
        ).first()
        
        if inventory:
            inventory.reserved_quantity += item_data["quantity"]
            inventory.available_quantity = inventory.quantity - inventory.reserved_quantity
    
    db.commit()
    db.refresh(db_order)
    return db_order


@app.get("/api/orders", response_model=PaginatedResponse, tags=["Orders"])
def get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[schema.OrderStatusEnum] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all orders with filtering"""
    query = db.query(models.Order).options(joinedload(models.Order.order_items))
    
    # Regular users can only see their own orders
    if current_user.role.value not in ["admin", "manager"]:
        query = query.filter(models.Order.user_id == current_user.id)
    elif user_id:
        query = query.filter(models.Order.user_id == user_id)
    
    if status:
        query = query.filter(models.Order.status == status.value)
    
    total = query.count()
    items = query.order_by(desc(models.Order.ordered_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    return PaginatedResponse.create(items, total, page, page_size)


@app.get("/api/orders/{order_id}", response_model=OrderResponse, tags=["Orders"])
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get order by ID"""
    order = db.query(models.Order).options(
        joinedload(models.Order.order_items)
    ).filter(models.Order.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check access
    if current_user.role.value not in ["admin", "manager"] and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return order


# ============================================
# ANALYTICS & REPORTING ROUTES (Complex Queries)
# ============================================
@app.get("/api/analytics/inventory-summary", response_model=List[InventorySummary], tags=["Analytics"])
def get_inventory_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get inventory summary by warehouse.
    
    Shows total products, quantities, and value per warehouse.
    Uses SQL aggregation with JOINs.
    """
    results = db.query(
        models.Warehouse.id,
        models.Warehouse.name,
        func.count(models.Inventory.product_id).label("total_products"),
        func.sum(models.Inventory.quantity).label("total_quantity"),
        func.sum(models.Inventory.quantity * models.Product.unit_price).label("total_value"),
        models.Warehouse.capacity_m3,
        models.Warehouse.current_utilization
    ).join(
        models.Inventory, models.Warehouse.id == models.Inventory.warehouse_id
    ).join(
        models.Product, models.Inventory.product_id == models.Product.id
    ).group_by(
        models.Warehouse.id
    ).all()
    
    return [
        InventorySummary(
            warehouse_id=r.id,
            warehouse_name=r.name,
            total_products=r.total_products or 0,
            total_quantity=r.total_quantity or 0,
            total_value=r.total_value or Decimal("0.00"),
            utilization_percent=r.current_utilization or Decimal("0.00")
        )
        for r in results
    ]


@app.get("/api/analytics/sales-summary", response_model=SalesSummary, tags=["Analytics"])
def get_sales_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"]))
):
    """
    Get sales summary with date range filtering.
    
    Uses complex aggregation queries for:
    - Total orders
    - Total revenue
    - Average order value
    - Orders by status
    """
    query = db.query(models.Order)
    
    if start_date:
        query = query.filter(models.Order.ordered_at >= start_date)
    if end_date:
        query = query.filter(models.Order.ordered_at <= end_date)
    
    # Get basic stats
    total_orders = query.count()
    total_revenue = query.with_entities(func.sum(models.Order.total_amount)).scalar() or Decimal("0")
    
    avg_order_value = Decimal("0") if total_orders == 0 else total_revenue / total_orders
    
    # Get orders by status
    status_counts = db.query(
        models.Order.status,
        func.count(models.Order.id)
    ).group_by(models.Order.status).all()
    
    orders_by_status = {status.value: count for status, count in status_counts}
    
    return SalesSummary(
        total_orders=total_orders,
        total_revenue=total_revenue,
        average_order_value=avg_order_value,
        orders_by_status=orders_by_status
    )


@app.get("/api/analytics/low-stock-alerts", response_model=List[LowStockAlert], tags=["Analytics"])
def get_low_stock_alerts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all products below reorder point.
    
    Uses subquery to find products needing reorder.
    """
    results = db.query(
        models.Product.id,
        models.Product.name,
        models.Product.sku,
        models.Inventory.warehouse_id,
        models.Warehouse.name,
        models.Inventory.quantity,
        models.Inventory.reorder_level
    ).join(
        models.Inventory, models.Product.id == models.Inventory.product_id
    ).join(
        models.Warehouse, models.Inventory.warehouse_id == models.Warehouse.id
    ).filter(
        models.Inventory.quantity < models.Inventory.reorder_level
    ).all()
    
    return [
        LowStockAlert(
            product_id=r.id,
            product_name=r.name,
            sku=r.sku,
            warehouse_id=r.warehouse_id,
            warehouse_name=r.name,
            current_quantity=r.quantity,
            reorder_level=r.reorder_level
        )
        for r in results
    ]


@app.get("/api/analytics/top-products", tags=["Analytics"])
def get_top_products(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get top selling products by order quantity.
    
    Uses complex join and aggregation.
    """
    results = db.query(
        models.Product.id,
        models.Product.name,
        models.Product.sku,
        models.Product.category,
        func.sum(models.OrderItem.quantity).label("total_sold"),
        func.count(models.OrderItem.order_id).label("order_count")
    ).join(
        models.OrderItem, models.Product.id == models.OrderItem.product_id
    ).join(
        models.Order, models.OrderItem.order_id == models.Order.id
    ).group_by(
        models.Product.id
    ).order_by(
        desc("total_sold")
    ).limit(limit).all()
    
    return [
        {
            "product_id": r.id,
            "name": r.name,
            "sku": r.sku,
            "category": r.category.value,
            "total_sold": r.total_sold,
            "order_count": r.order_count
        }
        for r in results
    ]


@app.get("/api/analytics/supplier-performance", tags=["Analytics"])
def get_supplier_performance(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"]))
):
    """
    Get supplier performance metrics.
    
    Shows supplier ratings, on-time delivery, and order counts.
    """
    results = db.query(
        models.Supplier.id,
        models.Supplier.company_name,
        models.Supplier.country,
        models.Supplier.rating,
        models.Supplier.on_time_delivery_rate,
        func.count(models.Shipment.id).label("shipment_count")
    ).outerjoin(
        models.Shipment, models.Supplier.id == models.Shipment.supplier_id
    ).group_by(
        models.Supplier.id
    ).order_by(
        desc(models.Supplier.rating)
    ).all()
    
    return [
        {
            "supplier_id": r.id,
            "company_name": r.company_name,
            "country": r.country,
            "rating": float(r.rating),
            "on_time_delivery_rate": float(r.on_time_delivery_rate),
            "shipment_count": r.shipment_count
        }
        for r in results
    ]


# ============================================
# Run the Application
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
