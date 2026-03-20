"""
Shipments Router
================
CRUD endpoints for shipment tracking.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

import models
import schema
from schema import (
    ShipmentCreate, ShipmentResponse, ShipmentUpdate,
    PaginatedResponse, ShipmentStatusEnum,
)
from auth import get_current_user, require_role
from database import get_db

router = APIRouter(prefix="/api/shipments", tags=["Shipments"])


@router.post("", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED)
def create_shipment(
    shipment: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager", "staff"])),
):
    """Create a new shipment."""
    db_shipment = models.Shipment(**shipment.model_dump())
    db.add(db_shipment)
    db.commit()
    db.refresh(db_shipment)
    return db_shipment


@router.get("", response_model=PaginatedResponse)
def get_shipments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: ShipmentStatusEnum | None = None,
    supplier_id: int | None = None,
    warehouse_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all shipments with filtering."""
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


@router.get("/{shipment_id}", response_model=ShipmentResponse)
def get_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get shipment by ID."""
    shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


@router.put("/{shipment_id}", response_model=ShipmentResponse)
def update_shipment(
    shipment_id: int,
    shipment: ShipmentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager", "staff"])),
):
    """Update shipment status."""
    db_shipment = db.query(models.Shipment).filter(models.Shipment.id == shipment_id).first()
    if not db_shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    update_data = shipment.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_shipment, key, value)

    db.commit()
    db.refresh(db_shipment)
    return db_shipment
