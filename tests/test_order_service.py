"""
Order service -- unit tests without HTTP.

The whole point of `services/orders.py` is that the business rules can be
exercised directly, with a session and a user, and no TestClient. These
tests document that boundary and cover the failure paths that would
otherwise only be reachable through carefully crafted HTTP payloads.
"""

from decimal import Decimal

import pytest

import models
from conftest import make_inventory, make_product, make_user
from schema import OrderCreate, OrderUpdate
from services import orders as order_service


def _payload(product_id, quantity=1, **overrides):
    data = {"items": [{"product_id": product_id, "quantity": quantity}]}
    data.update(overrides)
    return OrderCreate(**data)


def test_create_order_returns_a_domain_object(db_session, staff_user, warehouse):
    product = make_product(db_session, sku="SVC-1", unit_price="25.00")
    make_inventory(db_session, warehouse, product, quantity=10)

    order = order_service.create_order(db_session, staff_user, _payload(product.id, 2))

    assert isinstance(order, models.Order)
    assert order.user_id == staff_user.id
    assert order.status == models.OrderStatus.PENDING
    # 2 * 25.00 = 50.00, +20% tax = 10.00, +10.00 shipping (below 100.00)
    assert order.subtotal == Decimal("50.00")
    assert order.tax_amount == Decimal("10.00")
    assert order.shipping_cost == Decimal("10.00")
    assert order.total_amount == Decimal("70.00")


def test_price_comes_from_the_product_not_the_payload(
    db_session, staff_user, warehouse
):
    product = make_product(db_session, sku="SVC-2", unit_price="80.00")
    make_inventory(db_session, warehouse, product, quantity=10)

    payload = OrderCreate(
        items=[{"product_id": product.id, "quantity": 1, "unit_price": "0.01"}]
    )
    order = order_service.create_order(db_session, staff_user, payload)

    assert order.subtotal == Decimal("80.00")
    assert order.order_items[0].unit_price == Decimal("80.00")


def test_insufficient_stock_raises_and_rolls_back(db_session, staff_user, warehouse):
    product = make_product(db_session, sku="SVC-3", unit_price="10.00")
    inventory = make_inventory(db_session, warehouse, product, quantity=1)

    with pytest.raises(order_service.OrderConflict):
        order_service.create_order(db_session, staff_user, _payload(product.id, 5))

    db_session.refresh(inventory)
    assert inventory.reserved_quantity == 0
    assert inventory.available_quantity == 1
    assert db_session.query(models.Order).count() == 0


def test_regular_user_cannot_order_for_someone_else(db_session, staff_user, warehouse):
    other = make_user(db_session, "svc_other")
    product = make_product(db_session, sku="SVC-4", unit_price="10.00")
    make_inventory(db_session, warehouse, product, quantity=10)

    with pytest.raises(order_service.OrderForbidden):
        order_service.create_order(
            db_session, staff_user, _payload(product.id, user_id=other.id)
        )


def test_unknown_product_raises_not_found(db_session, staff_user):
    with pytest.raises(order_service.OrderNotFound):
        order_service.create_order(db_session, staff_user, _payload(999999))


def test_invalid_transition_raises_conflict(db_session, staff_user, warehouse):
    product = make_product(db_session, sku="SVC-5", unit_price="10.00")
    make_inventory(db_session, warehouse, product, quantity=10)
    order = order_service.create_order(db_session, staff_user, _payload(product.id))

    with pytest.raises(order_service.OrderConflict):
        order_service.update_order(
            db_session, staff_user, order.id, OrderUpdate(status="Delivered")
        )


def test_cancel_releases_stock_and_can_only_happen_once(
    db_session, staff_user, warehouse
):
    product = make_product(db_session, sku="SVC-6", unit_price="10.00")
    inventory = make_inventory(db_session, warehouse, product, quantity=10)
    order = order_service.create_order(db_session, staff_user, _payload(product.id, 4))

    order_service.cancel_order(db_session, staff_user, order.id)

    db_session.refresh(inventory)
    assert inventory.reserved_quantity == 0
    assert inventory.available_quantity == 10

    with pytest.raises(order_service.OrderConflict):
        order_service.cancel_order(db_session, staff_user, order.id)


def test_viewer_cannot_update_status(db_session, viewer_user, warehouse):
    owner = make_user(db_session, "svc_owner")
    product = make_product(db_session, sku="SVC-7", unit_price="10.00")
    make_inventory(db_session, warehouse, product, quantity=10)
    order = order_service.create_order(db_session, owner, _payload(product.id))

    with pytest.raises(order_service.OrderForbidden):
        order_service.update_order(
            db_session, viewer_user, order.id, OrderUpdate(status="Processing")
        )


def test_service_module_does_not_depend_on_fastapi():
    """The service must stay importable and testable outside the HTTP layer."""
    assert not hasattr(order_service, "APIRouter")
    assert not hasattr(order_service, "Depends")
