"""
Orders Router
=============
CRUD endpoints for order management with inventory reservation.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
from decimal import Decimal
from datetime import datetime

import models
from schema import (
    OrderCreate, OrderResponse, OrderUpdate,
    PaginatedResponse, OrderStatusEnum,
)
from auth import get_current_user, require_role
from database import get_db

router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new order with items and automatic inventory reservation."""
    user = db.query(models.User).filter(models.User.id == order.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    subtotal = Decimal("0.00")
    order_items_data = []

    for item in order.items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        discount_amount = item.unit_price * (item.discount_percent / 100)
        line_total = (item.unit_price - discount_amount) * item.quantity
        subtotal += line_total

        order_items_data.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "discount_percent": item.discount_percent,
            "line_total": line_total,
        })

    tax_rate = Decimal("0.20")
    tax_amount = subtotal * tax_rate
    shipping_cost = Decimal("10.00") if subtotal < Decimal("100.00") else Decimal("0.00")
    total_amount = subtotal + tax_amount + shipping_cost

    order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{int(datetime.utcnow().timestamp())}"

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
        status=models.OrderStatus.PENDING,
    )
    db.add(db_order)
    db.flush()

    for item_data in order_items_data:
        order_item = models.OrderItem(order_id=db_order.id, **item_data)
        db.add(order_item)

        inventory = db.query(models.Inventory).filter(
            and_(
                models.Inventory.product_id == item_data["product_id"],
                models.Inventory.available_quantity >= item_data["quantity"],
            )
        ).first()

        if inventory:
            inventory.reserved_quantity += item_data["quantity"]
            inventory.available_quantity = inventory.quantity - inventory.reserved_quantity

    db.commit()
    db.refresh(db_order)
    return db_order


@router.get("", response_model=PaginatedResponse)
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
    items = query.order_by(desc(models.Order.ordered_at)).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get order by ID."""
    order = db.query(models.Order).options(
        joinedload(models.Order.order_items)
    ).filter(models.Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role.value not in ["admin", "manager"] and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return order
