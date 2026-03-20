"""
Products Router
===============
CRUD endpoints for product catalog management.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from decimal import Decimal

import models
import schema
from schema import (
    ProductCreate, ProductResponse, ProductUpdate,
    ProductWithInventoryResponse, PaginatedResponse,
    ProductCategoryEnum,
)
from auth import get_current_user, require_role
from database import get_db

router = APIRouter(prefix="/api/products", tags=["Products"])


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"])),
):
    """Create a new product (Admin/Manager only)."""
    existing = db.query(models.Product).filter(models.Product.sku == product.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")

    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.get("", response_model=PaginatedResponse)
def get_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    category: ProductCategoryEnum | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    supplier_id: int | None = None,
    low_stock_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all products with advanced filtering and search."""
    query = db.query(models.Product)

    if search:
        query = query.filter(
            or_(
                models.Product.name.ilike(f"%{search}%"),
                models.Product.sku.ilike(f"%{search}%"),
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

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/{product_id}", response_model=ProductWithInventoryResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get product by ID with inventory summary."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    inventory_summary = db.query(
        func.count(models.Inventory.product_id).label("warehouses_count"),
        func.sum(models.Inventory.quantity).label("total_quantity"),
        func.sum(models.Inventory.available_quantity).label("available_quantity"),
    ).filter(models.Inventory.product_id == product_id).first()

    response = ProductWithInventoryResponse(
        **product.__dict__,
        total_quantity=inventory_summary.total_quantity or 0,
        available_quantity=inventory_summary.available_quantity or 0,
        warehouses_count=inventory_summary.warehouses_count or 0,
    )
    return response


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"])),
):
    """Update product (Admin/Manager only)."""
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)

    db.commit()
    db.refresh(db_product)
    return db_product
