"""
Inventory Router
================
CRUD endpoints for stock tracking and adjustments.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

import models
from schema import (
    InventoryCreate, InventoryResponse, InventoryUpdate,
    InventoryAdjustRequest, PaginatedResponse,
)
from auth import get_current_user, require_role
from database import get_db

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


@router.post("", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def create_inventory(
    inventory: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager", "staff"])),
):
    """Create inventory record (Admin/Manager/Staff)."""
    existing = db.query(models.Inventory).filter(
        and_(
            models.Inventory.warehouse_id == inventory.warehouse_id,
            models.Inventory.product_id == inventory.product_id,
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Inventory record already exists for this warehouse-product combination",
        )

    warehouse = db.query(models.Warehouse).filter(models.Warehouse.id == inventory.warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    product = db.query(models.Product).filter(models.Product.id == inventory.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    available = inventory.quantity - (inventory.reserved_quantity or 0)

    db_inventory = models.Inventory(**inventory.model_dump(), available_quantity=available)
    db.add(db_inventory)
    db.commit()
    db.refresh(db_inventory)
    return db_inventory


@router.get("", response_model=PaginatedResponse)
def get_inventory(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    warehouse_id: int | None = None,
    product_id: int | None = None,
    low_stock: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get inventory with filtering."""
    query = db.query(models.Inventory).options(
        joinedload(models.Inventory.warehouse),
        joinedload(models.Inventory.product),
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


@router.get("/warehouse/{warehouse_id}", response_model=PaginatedResponse)
def get_warehouse_inventory(
    warehouse_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all inventory for a specific warehouse with pagination."""
    query = db.query(models.Inventory).options(
        joinedload(models.Inventory.product)
    ).filter(models.Inventory.warehouse_id == warehouse_id)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse.create(items, total, page, page_size)


@router.post("/adjust", response_model=InventoryResponse)
def adjust_inventory(
    warehouse_id: int,
    product_id: int,
    adjustment: InventoryAdjustRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager", "staff"])),
):
    """Adjust inventory quantity (add or remove stock)."""
    inventory = db.query(models.Inventory).filter(
        and_(
            models.Inventory.warehouse_id == warehouse_id,
            models.Inventory.product_id == product_id,
        )
    ).first()

    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory record not found")

    new_quantity = inventory.quantity + adjustment.adjustment

    if new_quantity < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Current: {inventory.quantity}, Requested adjustment: {adjustment.adjustment}",
        )

    inventory.quantity = new_quantity
    inventory.available_quantity = new_quantity - inventory.reserved_quantity

    db.commit()
    db.refresh(inventory)
    return inventory
