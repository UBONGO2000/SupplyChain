"""
Order Services
==============
Business logic for order creation, stock reservation and lifecycle.

Why a service layer: the router should only translate HTTP into calls and
back. Keeping the rules here makes them testable without a TestClient and
makes the invariants explicit instead of buried in an endpoint:

- the price always comes from ``Product.unit_price``, never from the client;
- stock is reserved atomically (``SELECT ... FOR UPDATE``) before the order
  rows are written, so two concurrent orders cannot both take the last unit;
- status changes follow an explicit transition graph, and cancelling or
  shipping an order releases the reservation it holds.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

import models
from schema import OrderCreate, OrderUpdate

logger = logging.getLogger("supplychain.orders")

#: VAT applied to every order.
TAX_RATE = Decimal("0.20")
#: Orders at or above this subtotal ship for free.
FREE_SHIPPING_THRESHOLD = Decimal("100.00")
#: Flat shipping fee below the threshold.
SHIPPING_COST = Decimal("10.00")
#: Monetary values are rounded half-up to the cent, like the DECIMAL(12, 2)
#: columns that store them.
MONEY = Decimal("0.01")

#: Roles allowed to create or cancel an order on behalf of another user.
ORDER_MANAGER_ROLES = frozenset({"admin", "manager"})
#: Roles allowed to move an order through its lifecycle.
STATUS_UPDATE_ROLES = frozenset({"admin", "manager", "staff"})

#: Explicit lifecycle: PENDING -> PROCESSING -> SHIPPED -> DELIVERED.
#: Cancellation is only possible before the goods leave the warehouse.
ALLOWED_TRANSITIONS = {
    models.OrderStatus.PENDING: frozenset(
        {models.OrderStatus.PROCESSING, models.OrderStatus.CANCELLED}
    ),
    models.OrderStatus.PROCESSING: frozenset(
        {models.OrderStatus.SHIPPED, models.OrderStatus.CANCELLED}
    ),
    models.OrderStatus.SHIPPED: frozenset({models.OrderStatus.DELIVERED}),
    models.OrderStatus.DELIVERED: frozenset(),
    models.OrderStatus.CANCELLED: frozenset(),
}


# ============================================
# Domain Errors
# ============================================
class OrderError(Exception):
    """Base class for order business errors.

    The service layer deliberately does not import FastAPI: ``main.py`` maps
    these exceptions to HTTP responses, which keeps the rules usable from a
    CLI, a worker or a plain unit test.
    """

    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class OrderValidationError(OrderError):
    """The request is well-formed but cannot be applied."""

    status_code = 400


class OrderForbidden(OrderError):
    """The caller is not allowed to act on this order or user."""

    status_code = 403


class OrderNotFound(OrderError):
    """A referenced order, product or user does not exist."""

    status_code = 404


class OrderConflict(OrderError):
    """The request conflicts with the current state (stock, status...)."""

    status_code = 409


# ============================================
# Helpers
# ============================================
def _money(value) -> Decimal:
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def _has_role(user: models.User, roles: frozenset[str]) -> bool:
    return user.role.value in roles


def _inventory_rows(db: Session, product_id: int, *, only_reserved: bool = False):
    """Lock and return the inventory rows of a product, in a stable order.

    The ``order_by`` is not cosmetic: locking rows in a consistent order is
    what prevents two concurrent orders from deadlocking on each other.
    """
    query = db.query(models.Inventory).filter(models.Inventory.product_id == product_id)
    if only_reserved:
        query = query.filter(models.Inventory.reserved_quantity > 0)
    return query.order_by(models.Inventory.warehouse_id.asc()).with_for_update().all()


def _reserve_stock(db: Session, product_id: int, quantity: int) -> None:
    """Reserve ``quantity`` units of a product, across warehouses if needed.

    Raises :class:`OrderConflict` when the total available quantity is
    insufficient -- there is no silent "reserve nothing" path anymore.
    """
    rows = _inventory_rows(db, product_id)
    available = sum(row.available_quantity or 0 for row in rows)

    if available < quantity:
        raise OrderConflict(
            f"Insufficient stock for product {product_id}: "
            f"requested {quantity}, available {available}"
        )

    remaining = quantity
    for row in rows:
        take = min(row.available_quantity or 0, remaining)
        if take <= 0:
            continue
        row.reserved_quantity = (row.reserved_quantity or 0) + take
        row.available_quantity = row.quantity - row.reserved_quantity
        remaining -= take
        if remaining == 0:
            break


def _release_stock(db: Session, product_id: int, quantity: int, *, ship: bool) -> None:
    """Give back a reservation, optionally removing the goods from stock.

    ``ship=False`` (cancellation) only drops the reservation. ``ship=True``
    (order shipped) also decrements the physical quantity, because the goods
    have left the warehouse.
    """
    rows = _inventory_rows(db, product_id, only_reserved=True)
    remaining = quantity

    for row in rows:
        take = min(row.reserved_quantity or 0, remaining)
        if take <= 0:
            continue
        row.reserved_quantity -= take
        if ship:
            row.quantity -= take
        row.available_quantity = row.quantity - row.reserved_quantity
        remaining -= take
        if remaining == 0:
            break

    if remaining > 0:
        # Only reachable if the database was modified outside this service.
        logger.error(
            "Released %s/%s reserved units for product %s: reservation underflow",
            quantity - remaining,
            quantity,
            product_id,
        )


def _release_order(db: Session, order: models.Order, *, ship: bool) -> None:
    """Release every reservation held by an order, aggregated per product."""
    totals: dict[int, int] = {}
    for item in order.order_items:
        totals[item.product_id] = totals.get(item.product_id, 0) + item.quantity

    for product_id in sorted(totals):
        _release_stock(db, product_id, totals[product_id], ship=ship)


def _get_order(db: Session, order_id: int) -> models.Order:
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if order is None:
        raise OrderNotFound("Order not found")
    return order


def _assert_can_manage(user: models.User, order: models.Order) -> None:
    if _has_role(user, ORDER_MANAGER_ROLES):
        return
    if order.user_id != user.id:
        raise OrderForbidden("Access denied")


def _apply_status(
    db: Session, order: models.Order, new_status: models.OrderStatus
) -> None:
    current = order.status
    if current == new_status:
        raise OrderConflict(f"Order is already {new_status.value.lower()}")

    if new_status not in ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise OrderConflict(
            f"Cannot move an order from {current.value} to {new_status.value}"
        )

    if new_status is models.OrderStatus.CANCELLED:
        _release_order(db, order, ship=False)
    elif new_status is models.OrderStatus.SHIPPED:
        _release_order(db, order, ship=True)

    order.status = new_status
    now = datetime.now(timezone.utc)
    if new_status is models.OrderStatus.SHIPPED:
        order.shipped_at = now
    elif new_status is models.OrderStatus.DELIVERED:
        order.delivered_at = now


# ============================================
# Public API
# ============================================
def resolve_customer(
    db: Session, current_user: models.User, requested_user_id: int | None
) -> models.User:
    """Return the user the order belongs to.

    Regular users may only order for themselves; admin/manager may target
    someone else. The check is explicit (403) rather than silently ignoring
    the field, so a client never believes it ordered for another account.
    """
    target_id = requested_user_id or current_user.id

    if target_id != current_user.id and not _has_role(
        current_user, ORDER_MANAGER_ROLES
    ):
        raise OrderForbidden("You can only create orders for yourself")

    customer = db.get(models.User, target_id)
    if customer is None:
        raise OrderNotFound("User not found")
    if not customer.is_active:
        raise OrderValidationError("Cannot create an order for an inactive user")
    return customer


def create_order(
    db: Session, current_user: models.User, payload: OrderCreate
) -> models.Order:
    """Create an order with server-side pricing and atomic stock reservation."""
    customer = resolve_customer(db, current_user, payload.user_id)

    subtotal = Decimal("0.00")
    items: list[dict] = []
    requested_by_product: dict[int, int] = {}

    for item in payload.items:
        product = db.get(models.Product, item.product_id)
        if product is None:
            raise OrderNotFound(f"Product {item.product_id} not found")

        # The client's `unit_price` is accepted for backward compatibility but
        # never used: the price of record is the one in the database.
        unit_price = _money(product.unit_price)
        discount = Decimal(item.discount_percent or 0)
        line_total = _money(unit_price * (1 - discount / 100) * item.quantity)
        subtotal += line_total

        items.append(
            {
                "product_id": product.id,
                "quantity": item.quantity,
                "unit_price": unit_price,
                "discount_percent": discount,
                "line_total": line_total,
            }
        )
        requested_by_product[product.id] = (
            requested_by_product.get(product.id, 0) + item.quantity
        )

    subtotal = _money(subtotal)
    tax_amount = _money(subtotal * TAX_RATE)
    shipping_cost = (
        Decimal("0.00") if subtotal >= FREE_SHIPPING_THRESHOLD else SHIPPING_COST
    )
    total_amount = _money(subtotal + tax_amount + shipping_cost)

    try:
        # Deterministic lock order (sorted product ids) avoids deadlocks.
        for product_id in sorted(requested_by_product):
            _reserve_stock(db, product_id, requested_by_product[product_id])

        order = models.Order(
            order_number=(
                f"ORD-{datetime.now(timezone.utc):%Y%m%d}-"
                f"{uuid4().hex[:10].upper()}"
            ),
            user_id=customer.id,
            shipping_address=payload.shipping_address,
            billing_address=payload.billing_address,
            notes=payload.notes,
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_cost=shipping_cost,
            total_amount=total_amount,
            status=models.OrderStatus.PENDING,
        )
        db.add(order)
        db.flush()

        for item_data in items:
            db.add(models.OrderItem(order_id=order.id, **item_data))

        db.commit()
    except Exception:
        # No partial reservation must survive a failed order.
        db.rollback()
        raise

    db.refresh(order)
    return order


def update_order(
    db: Session,
    current_user: models.User,
    order_id: int,
    payload: OrderUpdate,
) -> models.Order:
    """Update an order's status and/or shipping details."""
    if not _has_role(current_user, STATUS_UPDATE_ROLES):
        raise OrderForbidden("You are not allowed to update orders")

    order = _get_order(db, order_id)

    if (
        payload.status is None
        and payload.shipping_address is None
        and payload.billing_address is None
        and payload.notes is None
    ):
        raise OrderValidationError("No updatable field provided")

    try:
        if payload.status is not None:
            _apply_status(db, order, models.OrderStatus(payload.status.value))
        if payload.shipping_address is not None:
            order.shipping_address = payload.shipping_address
        if payload.billing_address is not None:
            order.billing_address = payload.billing_address
        if payload.notes is not None:
            order.notes = payload.notes
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(order)
    return order


def cancel_order(db: Session, current_user: models.User, order_id: int) -> models.Order:
    """Cancel an order and release the stock it reserved."""
    order = _get_order(db, order_id)
    _assert_can_manage(current_user, order)

    try:
        _apply_status(db, order, models.OrderStatus.CANCELLED)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(order)
    return order
