"""
Orders Router
=============
HTTP layer for order management.

Business rules (pricing, stock reservation, status transitions) live in
``services.orders``; this module only translates HTTP requests into service
calls and shapes the responses.
"""

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

import models
from auth import get_current_user
from database import get_db
from schema import (
    OrderCreate,
    OrderResponse,
    OrderStatusEnum,
    OrderUpdate,
    PaginatedResponse,
)
from services import orders as order_service

router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.post("", response_model=OrderResponse, status_code=http_status.HTTP_201_CREATED)
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create an order.

    The server owns the price (from `Product.unit_price`) and reserves the
    stock atomically before writing the order.
    """
    return order_service.create_order(db, current_user, order)


@router.get("", response_model=PaginatedResponse[OrderResponse])
def get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: OrderStatusEnum | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all orders with filtering. Regular users see only their own orders."""
    query = db.query(models.Order).options(joinedload(models.Order.order_items))

    if current_user.role.value not in ["admin", "manager"]:
        query = query.filter(models.Order.user_id == current_user.id)
    elif user_id:
        query = query.filter(models.Order.user_id == user_id)

    if status:
        query = query.filter(models.Order.status == status.value)

    total = query.count()
    items = (
        # `id` as a tie-breaker keeps pagination stable when several orders
        # share the same timestamp (otherwise rows can be skipped/duplicated
        # between two pages).
        query.order_by(desc(models.Order.ordered_at), desc(models.Order.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get order by ID."""
    order = (
        db.query(models.Order)
        .options(joinedload(models.Order.order_items))
        .filter(models.Order.id == order_id)
        .first()
    )

    if not order:
        raise order_service.OrderNotFound("Order not found")

    if (
        current_user.role.value not in ["admin", "manager"]
        and order.user_id != current_user.id
    ):
        raise order_service.OrderForbidden("Access denied")

    return order


@router.patch("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: int,
    payload: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update an order's status and/or shipping details (admin/manager/staff).

    Status changes are validated against an explicit lifecycle:
    PENDING -> PROCESSING -> SHIPPED -> DELIVERED, with CANCELLED allowed
    only before shipping.
    """
    return order_service.update_order(db, current_user, order_id, payload)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Cancel an order and release the stock it reserved."""
    return order_service.cancel_order(db, current_user, order_id)
