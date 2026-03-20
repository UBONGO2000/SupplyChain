"""
Warehouses Router
=================
CRUD endpoints for warehouse management.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

import models
from schema import WarehouseCreate, WarehouseResponse, WarehouseUpdate, PaginatedResponse, MessageResponse
from auth import get_current_user, require_role
from database import get_db

router = APIRouter(prefix="/api/warehouses", tags=["Warehouses"])


@router.post("", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    warehouse: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"])),
):
    """Create a new warehouse (Admin/Manager only)."""
    db_warehouse = models.Warehouse(**warehouse.model_dump())
    db.add(db_warehouse)
    db.commit()
    db.refresh(db_warehouse)
    return db_warehouse


@router.get("", response_model=PaginatedResponse)
def get_warehouses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all warehouses with pagination and filtering."""
    query = db.query(models.Warehouse)

    if search:
        query = query.filter(
            or_(
                models.Warehouse.name.ilike(f"%{search}%"),
                models.Warehouse.location.ilike(f"%{search}%"),
            )
        )

    if is_active is not None:
        query = query.filter(models.Warehouse.is_active == is_active)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
def get_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get warehouse by ID."""
    warehouse = db.query(models.Warehouse).filter(models.Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return warehouse


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(
    warehouse_id: int,
    warehouse: WarehouseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"])),
):
    """Update warehouse (Admin/Manager only)."""
    db_warehouse = db.query(models.Warehouse).filter(models.Warehouse.id == warehouse_id).first()
    if not db_warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    update_data = warehouse.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_warehouse, key, value)

    db.commit()
    db.refresh(db_warehouse)
    return db_warehouse


@router.delete("/{warehouse_id}", response_model=MessageResponse)
def delete_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin"])),
):
    """Delete warehouse (Admin only)."""
    warehouse = db.query(models.Warehouse).filter(models.Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    inventory_count = db.query(models.Inventory).filter(models.Inventory.warehouse_id == warehouse_id).count()
    if inventory_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete warehouse with existing inventory. Transfer inventory first.",
        )

    db.delete(warehouse)
    db.commit()
    return MessageResponse(message="Warehouse deleted successfully")
