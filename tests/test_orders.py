"""
Priority 2 -- Order business logic.

Covers total calculation, stock reservation (including the known bug where
an order for a product with zero matching inventory is silently created
with no reservation and no error), 404s on bad references, and
order-visibility / IDOR checks.
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


def _item(product_id, quantity, unit_price, discount_percent="0.00"):
    return {
        "product_id": product_id,
        "quantity": quantity,
        "unit_price": unit_price,
        "discount_percent": discount_percent,
    }


# ============================================
# Total calculation
# ============================================
class TestOrderTotals:
    def test_totals_below_free_shipping_threshold(self, client, staff_user, db_session, warehouse):
        product = make_product(db_session, sku="CALC-1", unit_price="20.00")
        make_inventory(db_session, warehouse, product, quantity=50)

        payload = _order_payload(staff_user.id, [_item(product.id, 2, "20.00")])
        resp = client.post("/api/orders", json=payload, headers=auth_headers(staff_user))

        assert resp.status_code == 201
        body = resp.json()
        # subtotal = 2 * 20.00 = 40.00 (< 100 -> shipping applies)
        assert Decimal(body["subtotal"]) == Decimal("40.00")
        assert Decimal(body["tax_amount"]) == Decimal("8.00")  # 20%
        assert Decimal(body["shipping_cost"]) == Decimal("10.00")
        assert Decimal(body["total_amount"]) == Decimal("58.00")

    def test_totals_at_or_above_free_shipping_threshold(self, client, staff_user, db_session, warehouse):
        product = make_product(db_session, sku="CALC-2", unit_price="50.00")
        make_inventory(db_session, warehouse, product, quantity=50)

        payload = _order_payload(staff_user.id, [_item(product.id, 2, "50.00")])
        resp = client.post("/api/orders", json=payload, headers=auth_headers(staff_user))

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
        resp = client.post("/api/orders", json=payload, headers=auth_headers(staff_user))

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
        resp = client.post("/api/orders", json=payload, headers=auth_headers(staff_user))

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
        inv = make_inventory(db_session, warehouse, product, quantity=50, reserved_quantity=5)
        # available_quantity starts at 45

        payload = _order_payload(staff_user.id, [_item(product.id, 7, "15.00")])
        resp = client.post("/api/orders", json=payload, headers=auth_headers(staff_user))

        assert resp.status_code == 201

        db_session.refresh(inv)
        assert inv.reserved_quantity == 12  # 5 + 7
        assert inv.available_quantity == 38  # 50 - 12
        assert inv.quantity == 50  # untouched by reservation

    def test_order_on_product_with_no_matching_inventory_is_rejected(
        self, client, staff_user, db_session
    ):
        """
        The documented bug: ordering a product that has NO inventory record
        with enough available stock (here: no inventory record at all)
        currently succeeds silently with no reservation. This test encodes
        the desired, correct behavior -- an explicit 4xx -- and will fail
        until orders.py is fixed to reject the order instead of creating it.
        """
        product = make_product(db_session, sku="NO-STOCK-1", unit_price="10.00")
        # Deliberately no Inventory row created for this product at all.

        orders_before = db_session.query(models.Order).count()
        order_items_before = db_session.query(models.OrderItem).count()

        payload = _order_payload(staff_user.id, [_item(product.id, 1, "10.00")])
        resp = client.post("/api/orders", json=payload, headers=auth_headers(staff_user))

        assert resp.status_code in (400, 409)
        assert db_session.query(models.Order).count() == orders_before
        assert db_session.query(models.OrderItem).count() == order_items_before

    def test_unknown_product_id_returns_404(self, client, staff_user):
        payload = _order_payload(staff_user.id, [_item(999999, 1, "10.00")])
        resp = client.post("/api/orders", json=payload, headers=auth_headers(staff_user))

        assert resp.status_code == 404

    def test_unknown_user_id_returns_404(self, client, staff_user, db_session, warehouse):
        product = make_product(db_session, sku="UNK-USER", unit_price="10.00")
        make_inventory(db_session, warehouse, product, quantity=50)

        payload = _order_payload(999999, [_item(product.id, 1, "10.00")])
        resp = client.post("/api/orders", json=payload, headers=auth_headers(staff_user))

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

    def test_admin_can_filter_orders_by_user_id(self, client, db_session, warehouse, admin_user):
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

        resp = client.get(f"/api/orders?user_id={user_b.id}", headers=auth_headers(admin_user))

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

    def test_admin_can_access_any_order(self, client, db_session, warehouse, admin_user):
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
