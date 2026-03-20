"""
Suppliers Router
================
CRUD endpoints for supplier management.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session

import models
from schema import SupplierCreate, SupplierResponse, SupplierUpdate, PaginatedResponse
from auth import get_current_user, require_role
from database import get_db

router = APIRouter(prefix="/api/suppliers", tags=["Suppliers"])


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(
    supplier: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"])),
):
    """Create a new supplier (Admin/Manager only)."""
    db_supplier = models.Supplier(**supplier.model_dump())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


@router.get("", response_model=PaginatedResponse)
def get_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    country: str | None = None,
    min_rating: float | None = Query(None, ge=0, le=5),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all suppliers with advanced filtering."""
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


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get supplier by ID."""
    supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: int,
    supplier: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"])),
):
    """Update supplier (Admin/Manager only)."""
    db_supplier = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    update_data = supplier.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_supplier, key, value)

    db.commit()
    db.refresh(db_supplier)
    return db_supplier
