"""
Priority 2 -- Order business logic.

Covers server-side pricing, atomic stock reservation, order ownership,
status transitions and cancellation (which releases reserved stock), plus
404s on bad references and order-visibility / IDOR checks.
"""

from decimal import Decimal

import models
from conftest import auth_headers, make_product, make_inventory, make_user


def _order_payload(user_id, items, **overrides):
    payload = {
        "user_id": user_id,
        "items": items,
        "shipping_address": "1 Test Street",
    }
    payload.update(overrides)
    return payload


def _item(product_id, quantity, unit_price=None, discount_percent="0.00"):
    item = {
        "product_id": product_id,
        "quantity": quantity,
        "discount_percent": discount_percent,
    }
    if unit_price is not None:
        item["unit_price"] = unit_price
    return item


# ============================================
# Total calculation
# ============================================
class TestOrderTotals:
    def test_totals_below_free_shipping_threshold(
        self, client, staff_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="CALC-1", unit_price="20.00")
        make_inventory(db_session, warehouse, product, quantity=50)

        payload = _order_payload(staff_user.id, [_item(product.id, 2, "20.00")])
        resp = client.post(
            "/api/orders", json=payload, headers=auth_headers(staff_user)
        )

        assert resp.status_code == 201
        body = resp.json()
        # subtotal = 2 * 20.00 = 40.00 (< 100 -> shipping applies)
        assert Decimal(body["subtotal"]) == Decimal("40.00")
        assert Decimal(body["tax_amount"]) == Decimal("8.00")  # 20%
        assert Decimal(body["shipping_cost"]) == Decimal("10.00")
        assert Decimal(body["total_amount"]) == Decimal("58.00")

    def test_totals_at_or_above_free_shipping_threshold(
        self, client, staff_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="CALC-2", unit_price="50.00")
        make_inventory(db_session, warehouse, product, quantity=50)

        payload = _order_payload(staff_user.id, [_item(product.id, 2, "50.00")])
        resp = client.post(
            "/api/orders", json=payload, headers=auth_headers(staff_user)
        )

        assert resp.status_code == 201
        body = resp.json()
        # subtotal = 100.00 (>= 100 -> free shipping)
        assert Decimal(body["subtotal"]) == Decimal("100.00")
        assert Decimal(body["tax_amount"]) == Decimal("20.00")
        assert Decimal(body["shipping_cost"]) == Decimal("0.00")
        assert Decimal(body["total_amount"]) == Decimal("120.00")

    def test_totals_with_discount(self, client, staff_user, db_session, warehouse):
        product = make_product(db_session, sku="CALC-3", unit_price="100.00")
        make_inventory(db_session, warehouse, product, quantity=50)

        payload = _order_payload(
            staff_user.id, [_item(product.id, 1, "100.00", discount_percent="10.00")]
        )
        resp = client.post(
            "/api/orders", json=payload, headers=auth_headers(staff_user)
        )

        assert resp.status_code == 201
        body = resp.json()
        # line_total = (100 - 10%) * 1 = 90.00 -> still under 100 -> shipping applies
        assert Decimal(body["subtotal"]) == Decimal("90.00")
        assert Decimal(body["tax_amount"]) == Decimal("18.00")
        assert Decimal(body["shipping_cost"]) == Decimal("10.00")
        assert Decimal(body["total_amount"]) == Decimal("118.00")

    def test_totals_multiple_items(self, client, staff_user, db_session, warehouse):
        p1 = make_product(db_session, sku="CALC-4A", unit_price="30.00")
        p2 = make_product(db_session, sku="CALC-4B", unit_price="45.00")
        make_inventory(db_session, warehouse, p1, quantity=50)
        make_inventory(db_session, warehouse, p2, quantity=50)

        payload = _order_payload(
            staff_user.id,
            [_item(p1.id, 1, "30.00"), _item(p2.id, 2, "45.00")],
        )
        resp = client.post(
            "/api/orders", json=payload, headers=auth_headers(staff_user)
        )

        assert resp.status_code == 201
        body = resp.json()
        # subtotal = 30 + 2*45 = 120.00 -> free shipping
        assert Decimal(body["subtotal"]) == Decimal("120.00")
        assert Decimal(body["shipping_cost"]) == Decimal("0.00")
        assert Decimal(body["total_amount"]) == Decimal("144.00")


# ============================================
# Stock reservation
# ============================================
class TestStockReservation:
    def test_reservation_reduces_available_and_increases_reserved(
        self, client, staff_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="RES-1", unit_price="15.00")
        inv = make_inventory(
            db_session, warehouse, product, quantity=50, reserved_quantity=5
        )
        # available_quantity starts at 45

        payload = _order_payload(staff_user.id, [_item(product.id, 7, "15.00")])
        resp = client.post(
            "/api/orders", json=payload, headers=auth_headers(staff_user)
        )

        assert resp.status_code == 201

        db_session.refresh(inv)
        assert inv.reserved_quantity == 12  # 5 + 7
        assert inv.available_quantity == 38  # 50 - 12
        assert inv.quantity == 50  # untouched by reservation

    def test_order_on_product_with_no_matching_inventory_is_rejected(
        self, client, staff_user, db_session
    ):
        """Ordering a product with no inventory row must be an explicit 409.

        This is the regression test for the bug where such an order was
        created silently, with no reservation and no error.
        """
        product = make_product(db_session, sku="NO-STOCK-1", unit_price="10.00")
        # Deliberately no Inventory row created for this product at all.

        orders_before = db_session.query(models.Order).count()
        order_items_before = db_session.query(models.OrderItem).count()

        payload = _order_payload(staff_user.id, [_item(product.id, 1, "10.00")])
        resp = client.post(
            "/api/orders", json=payload, headers=auth_headers(staff_user)
        )

        assert resp.status_code in (400, 409)
        assert db_session.query(models.Order).count() == orders_before
        assert db_session.query(models.OrderItem).count() == order_items_before

    def test_unknown_product_id_returns_404(self, client, staff_user):
        payload = _order_payload(staff_user.id, [_item(999999, 1, "10.00")])
        resp = client.post(
            "/api/orders", json=payload, headers=auth_headers(staff_user)
        )

        assert resp.status_code == 404

    def test_unknown_user_id_returns_404(
        self, client, admin_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="UNK-USER", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=50)

        payload = _order_payload(999999, [_item(product.id, 1, "10.00")])
        resp = client.post(
            "/api/orders", json=payload, headers=auth_headers(admin_user)
        )

        assert resp.status_code == 404


# ============================================
# Visibility / IDOR
# ============================================
class TestOrderVisibility:
    def test_regular_user_only_sees_own_orders_in_list(
        self, client, db_session, warehouse
    ):
        user_a = make_user(db_session, "order_user_a")
        user_b = make_user(db_session, "order_user_b")
        product = make_product(db_session, sku="VIS-1", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=50)

        client.post(
            "/api/orders",
            json=_order_payload(user_a.id, [_item(product.id, 1, "10.00")]),
            headers=auth_headers(user_a),
        )
        client.post(
            "/api/orders",
            json=_order_payload(user_b.id, [_item(product.id, 1, "10.00")]),
            headers=auth_headers(user_b),
        )

        resp = client.get("/api/orders", headers=auth_headers(user_a))

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert all(item["user_id"] == user_a.id for item in body["items"])

    def test_admin_can_filter_orders_by_user_id(
        self, client, db_session, warehouse, admin_user
    ):
        user_a = make_user(db_session, "order_user_c")
        user_b = make_user(db_session, "order_user_d")
        product = make_product(db_session, sku="VIS-2", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=50)

        client.post(
            "/api/orders",
            json=_order_payload(user_a.id, [_item(product.id, 1, "10.00")]),
            headers=auth_headers(user_a),
        )
        client.post(
            "/api/orders",
            json=_order_payload(user_b.id, [_item(product.id, 1, "10.00")]),
            headers=auth_headers(user_b),
        )

        resp = client.get(
            f"/api/orders?user_id={user_b.id}", headers=auth_headers(admin_user)
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["user_id"] == user_b.id

    def test_non_owner_non_admin_gets_403_on_get_order(
        self, client, db_session, warehouse
    ):
        owner = make_user(db_session, "order_owner")
        intruder = make_user(db_session, "order_intruder")
        product = make_product(db_session, sku="IDOR-1", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=50)

        create_resp = client.post(
            "/api/orders",
            json=_order_payload(owner.id, [_item(product.id, 1, "10.00")]),
            headers=auth_headers(owner),
        )
        order_id = create_resp.json()["id"]

        resp = client.get(f"/api/orders/{order_id}", headers=auth_headers(intruder))

        assert resp.status_code == 403

    def test_admin_can_access_any_order(
        self, client, db_session, warehouse, admin_user
    ):
        owner = make_user(db_session, "order_owner_2")
        product = make_product(db_session, sku="IDOR-2", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=50)

        create_resp = client.post(
            "/api/orders",
            json=_order_payload(owner.id, [_item(product.id, 1, "10.00")]),
            headers=auth_headers(owner),
        )
        order_id = create_resp.json()["id"]

        resp = client.get(f"/api/orders/{order_id}", headers=auth_headers(admin_user))

        assert resp.status_code == 200
        assert resp.json()["id"] == order_id


# ============================================
# Server-side pricing
# ============================================
class TestServerSidePricing:
    def test_client_supplied_price_is_ignored(
        self, client, staff_user, db_session, warehouse
    ):
        """A client cannot buy a 100.00 product for 0.01."""
        product = make_product(db_session, sku="PRICE-1", unit_price="100.00")
        make_inventory(db_session, warehouse, product, quantity=10)

        payload = _order_payload(staff_user.id, [_item(product.id, 2, "0.01")])
        resp = client.post(
            "/api/orders", json=payload, headers=auth_headers(staff_user)
        )

        assert resp.status_code == 201
        body = resp.json()
        assert Decimal(body["subtotal"]) == Decimal("200.00")
        assert Decimal(body["total_amount"]) == Decimal("240.00")
        assert Decimal(body["order_items"][0]["unit_price"]) == Decimal("100.00")

    def test_unit_price_is_optional_and_taken_from_the_product(
        self, client, staff_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="PRICE-2", unit_price="30.00")
        make_inventory(db_session, warehouse, product, quantity=10)

        payload = _order_payload(staff_user.id, [_item(product.id, 1)])
        resp = client.post(
            "/api/orders", json=payload, headers=auth_headers(staff_user)
        )

        assert resp.status_code == 201
        body = resp.json()
        assert Decimal(body["order_items"][0]["unit_price"]) == Decimal("30.00")
        # 30.00 + 20% tax + 10.00 shipping
        assert Decimal(body["total_amount"]) == Decimal("46.00")

    def test_unknown_item_field_is_rejected(
        self, client, staff_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="PRICE-3", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=10)

        item = _item(product.id, 1)
        item["price"] = "1.00"
        resp = client.post(
            "/api/orders",
            json=_order_payload(staff_user.id, [item]),
            headers=auth_headers(staff_user),
        )

        assert resp.status_code == 422


# ============================================
# Order ownership
# ============================================
class TestOrderOwnership:
    def test_order_defaults_to_the_authenticated_user(
        self, client, staff_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="OWN-1", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=10)

        payload = {
            "items": [_item(product.id, 1)],
            "shipping_address": "1 Test Street",
        }
        resp = client.post(
            "/api/orders", json=payload, headers=auth_headers(staff_user)
        )

        assert resp.status_code == 201
        assert resp.json()["user_id"] == staff_user.id

    def test_staff_cannot_create_an_order_for_someone_else(
        self, client, staff_user, db_session, warehouse
    ):
        other = make_user(db_session, "order_other")
        product = make_product(db_session, sku="OWN-2", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=10)

        payload = _order_payload(other.id, [_item(product.id, 1)])
        resp = client.post(
            "/api/orders", json=payload, headers=auth_headers(staff_user)
        )

        assert resp.status_code == 403
        assert db_session.query(models.Order).count() == 0

    def test_admin_can_create_an_order_for_someone_else(
        self, client, admin_user, db_session, warehouse
    ):
        other = make_user(db_session, "order_other_2")
        product = make_product(db_session, sku="OWN-3", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=10)

        payload = _order_payload(other.id, [_item(product.id, 1)])
        resp = client.post(
            "/api/orders", json=payload, headers=auth_headers(admin_user)
        )

        assert resp.status_code == 201
        assert resp.json()["user_id"] == other.id


# ============================================
# Reservation under contention
# ============================================
class TestReservationContention:
    def test_second_order_for_the_last_unit_is_rejected(
        self, client, staff_user, db_session, warehouse
    ):
        """Only one of two orders for a single available unit may succeed.

        The guarantee is enforced by `SELECT ... FOR UPDATE` in
        services.orders._reserve_stock. On MySQL the row lock serialises the
        two transactions; on the SQLite test database the clause is a no-op
        but writes are serialised anyway, so the invariant is checked
        deterministically here.
        """
        product = make_product(db_session, sku="LAST-1", unit_price="10.00")
        inventory = make_inventory(db_session, warehouse, product, quantity=1)

        payload = _order_payload(staff_user.id, [_item(product.id, 1)])
        first = client.post(
            "/api/orders", json=payload, headers=auth_headers(staff_user)
        )
        second = client.post(
            "/api/orders", json=payload, headers=auth_headers(staff_user)
        )

        assert first.status_code == 201
        assert second.status_code == 409
        assert "insufficient stock" in second.json()["detail"].lower()

        db_session.refresh(inventory)
        assert inventory.reserved_quantity == 1
        assert inventory.available_quantity == 0
        assert db_session.query(models.Order).count() == 1


# ============================================
# Status transitions
# ============================================
def _create_order(client, user, product, quantity=1):
    resp = client.post(
        "/api/orders",
        json=_order_payload(user.id, [_item(product.id, quantity)]),
        headers=auth_headers(user),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestStatusTransitions:
    def test_pending_to_processing(self, client, staff_user, db_session, warehouse):
        product = make_product(db_session, sku="TRANS-1", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=10)
        order_id = _create_order(client, staff_user, product)

        resp = client.patch(
            f"/api/orders/{order_id}",
            json={"status": "Processing"},
            headers=auth_headers(staff_user),
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "Processing"

    def test_pending_to_delivered_is_rejected(
        self, client, staff_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="TRANS-2", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=10)
        order_id = _create_order(client, staff_user, product)

        resp = client.patch(
            f"/api/orders/{order_id}",
            json={"status": "Delivered"},
            headers=auth_headers(staff_user),
        )

        assert resp.status_code == 409
        assert "cannot move" in resp.json()["detail"].lower()

    def test_shipping_decrements_quantity_and_clears_reservation(
        self, client, staff_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="TRANS-3", unit_price="10.00")
        inventory = make_inventory(db_session, warehouse, product, quantity=10)
        order_id = _create_order(client, staff_user, product, quantity=4)

        db_session.refresh(inventory)
        assert inventory.reserved_quantity == 4
        assert inventory.available_quantity == 6

        for new_status in ("Processing", "Shipped"):
            resp = client.patch(
                f"/api/orders/{order_id}",
                json={"status": new_status},
                headers=auth_headers(staff_user),
            )
            assert resp.status_code == 200

        db_session.refresh(inventory)
        assert inventory.quantity == 6  # goods left the warehouse
        assert inventory.reserved_quantity == 0
        assert inventory.available_quantity == 6

        shipped = client.get(
            f"/api/orders/{order_id}", headers=auth_headers(staff_user)
        )
        assert shipped.json()["shipped_at"] is not None

    def test_delivered_sets_delivered_at(
        self, client, staff_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="TRANS-4", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=10)
        order_id = _create_order(client, staff_user, product)

        for new_status in ("Processing", "Shipped", "Delivered"):
            resp = client.patch(
                f"/api/orders/{order_id}",
                json={"status": new_status},
                headers=auth_headers(staff_user),
            )
            assert resp.status_code == 200

        body = resp.json()
        assert body["status"] == "Delivered"
        assert body["delivered_at"] is not None

    def test_same_status_is_rejected(self, client, staff_user, db_session, warehouse):
        product = make_product(db_session, sku="TRANS-5", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=10)
        order_id = _create_order(client, staff_user, product)

        resp = client.patch(
            f"/api/orders/{order_id}",
            json={"status": "Pending"},
            headers=auth_headers(staff_user),
        )

        assert resp.status_code == 409

    def test_viewer_cannot_update_a_status(
        self, client, viewer_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="TRANS-6", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=10)
        order_id = _create_order(client, viewer_user, product)

        resp = client.patch(
            f"/api/orders/{order_id}",
            json={"status": "Processing"},
            headers=auth_headers(viewer_user),
        )

        assert resp.status_code == 403

    def test_unknown_status_is_rejected(
        self, client, staff_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="TRANS-7", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=10)
        order_id = _create_order(client, staff_user, product)

        resp = client.patch(
            f"/api/orders/{order_id}",
            json={"status": "Teleported"},
            headers=auth_headers(staff_user),
        )

        assert resp.status_code == 422

    def test_missing_order_returns_404(self, client, staff_user):
        resp = client.patch(
            "/api/orders/999999",
            json={"status": "Processing"},
            headers=auth_headers(staff_user),
        )

        assert resp.status_code == 404

    def test_shipped_at_cannot_be_set_by_the_client(
        self, client, staff_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="TRANS-8", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=10)
        order_id = _create_order(client, staff_user, product)

        resp = client.patch(
            f"/api/orders/{order_id}",
            json={"shipped_at": "2020-01-01T00:00:00"},
            headers=auth_headers(staff_user),
        )

        assert resp.status_code == 422


# ============================================
# Cancellation
# ============================================
class TestCancelOrder:
    def test_cancel_releases_the_reserved_stock(
        self, client, staff_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="CANCEL-1", unit_price="10.00")
        inventory = make_inventory(db_session, warehouse, product, quantity=10)
        order_id = _create_order(client, staff_user, product, quantity=3)

        db_session.refresh(inventory)
        assert inventory.reserved_quantity == 3
        assert inventory.available_quantity == 7

        resp = client.post(
            f"/api/orders/{order_id}/cancel", headers=auth_headers(staff_user)
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "Cancelled"

        db_session.refresh(inventory)
        assert inventory.quantity == 10
        assert inventory.reserved_quantity == 0
        assert inventory.available_quantity == 10

    def test_cancelling_twice_returns_409(
        self, client, staff_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="CANCEL-2", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=10)
        order_id = _create_order(client, staff_user, product)

        first = client.post(
            f"/api/orders/{order_id}/cancel", headers=auth_headers(staff_user)
        )
        second = client.post(
            f"/api/orders/{order_id}/cancel", headers=auth_headers(staff_user)
        )

        assert first.status_code == 200
        assert second.status_code == 409

    def test_cancelling_a_shipped_order_is_rejected(
        self, client, staff_user, db_session, warehouse
    ):
        product = make_product(db_session, sku="CANCEL-3", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=10)
        order_id = _create_order(client, staff_user, product)

        for new_status in ("Processing", "Shipped"):
            client.patch(
                f"/api/orders/{order_id}",
                json={"status": new_status},
                headers=auth_headers(staff_user),
            )

        resp = client.post(
            f"/api/orders/{order_id}/cancel", headers=auth_headers(staff_user)
        )

        assert resp.status_code == 409

    def test_non_owner_cannot_cancel(self, client, db_session, warehouse):
        owner = make_user(db_session, "cancel_owner")
        intruder = make_user(db_session, "cancel_intruder")
        product = make_product(db_session, sku="CANCEL-4", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=10)
        order_id = _create_order(client, owner, product)

        resp = client.post(
            f"/api/orders/{order_id}/cancel", headers=auth_headers(intruder)
        )

        assert resp.status_code == 403

    def test_admin_can_cancel_any_order(
        self, client, db_session, warehouse, admin_user
    ):
        owner = make_user(db_session, "cancel_owner_2")
        product = make_product(db_session, sku="CANCEL-5", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=10)
        order_id = _create_order(client, owner, product)

        resp = client.post(
            f"/api/orders/{order_id}/cancel", headers=auth_headers(admin_user)
        )

        assert resp.status_code == 200

    def test_cancel_missing_order_returns_404(self, client, staff_user):
        resp = client.post(
            "/api/orders/999999/cancel", headers=auth_headers(staff_user)
        )

        assert resp.status_code == 404


# ============================================
# Pagination
# ============================================
def test_pagination_is_stable_across_pages(client, staff_user, db_session, warehouse):
    """Orders created in the same second must not be skipped or duplicated."""
    product = make_product(db_session, sku="PAGE-1", unit_price="10.00")
    make_inventory(db_session, warehouse, product, quantity=50)
    for _ in range(3):
        _create_order(client, staff_user, product)

    page1 = client.get(
        "/api/orders?page=1&page_size=2", headers=auth_headers(staff_user)
    ).json()
    page2 = client.get(
        "/api/orders?page=2&page_size=2", headers=auth_headers(staff_user)
    ).json()

    seen = [order["id"] for order in page1["items"] + page2["items"]]
    assert len(seen) == 3
    assert len(set(seen)) == 3
