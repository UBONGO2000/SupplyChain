"""
Priority 3 -- Inventory adjustment (data integrity).
"""

from conftest import auth_headers, make_inventory


class TestInventoryAdjust:
    def test_positive_adjustment_updates_quantity_and_available(
        self, client, staff_user, db_session, warehouse, product
    ):
        inv = make_inventory(
            db_session, warehouse, product, quantity=50, reserved_quantity=5
        )
        # available_quantity starts at 45

        resp = client.post(
            f"/api/inventory/adjust?warehouse_id={warehouse.id}&product_id={product.id}",
            json={"adjustment": 10, "reason": "restock"},
            headers=auth_headers(staff_user),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["quantity"] == 60
        assert body["available_quantity"] == 55  # 60 - 5 reserved

        db_session.refresh(inv)
        assert inv.quantity == 60
        assert inv.available_quantity == 55

    def test_negative_adjustment_below_zero_rejected_and_state_unchanged(
        self, client, staff_user, db_session, warehouse, product
    ):
        inv = make_inventory(
            db_session, warehouse, product, quantity=10, reserved_quantity=0
        )

        resp = client.post(
            f"/api/inventory/adjust?warehouse_id={warehouse.id}&product_id={product.id}",
            json={"adjustment": -20, "reason": "damaged goods"},
            headers=auth_headers(staff_user),
        )

        assert resp.status_code == 400

        db_session.refresh(inv)
        assert inv.quantity == 10
        assert inv.available_quantity == 10
        assert inv.reserved_quantity == 0

    def test_adjust_nonexistent_inventory_record_returns_404(
        self, client, staff_user, warehouse, product
    ):
        resp = client.post(
            f"/api/inventory/adjust?warehouse_id={warehouse.id}&product_id={product.id}",
            json={"adjustment": 5},
            headers=auth_headers(staff_user),
        )

        assert resp.status_code == 404

    def test_duplicate_inventory_record_rejected(
        self, client, staff_user, db_session, warehouse, product
    ):
        make_inventory(db_session, warehouse, product, quantity=20)

        resp = client.post(
            "/api/inventory",
            json={
                "warehouse_id": warehouse.id,
                "product_id": product.id,
                "quantity": 5,
            },
            headers=auth_headers(staff_user),
        )

        assert resp.status_code == 400

    def test_staff_can_adjust_inventory(
        self, client, staff_user, db_session, warehouse, product
    ):
        make_inventory(db_session, warehouse, product, quantity=20)

        resp = client.post(
            f"/api/inventory/adjust?warehouse_id={warehouse.id}&product_id={product.id}",
            json={"adjustment": 5},
            headers=auth_headers(staff_user),
        )

        assert resp.status_code == 200

    def test_viewer_cannot_adjust_inventory(
        self, client, viewer_user, db_session, warehouse, product
    ):
        make_inventory(db_session, warehouse, product, quantity=20)

        resp = client.post(
            f"/api/inventory/adjust?warehouse_id={warehouse.id}&product_id={product.id}",
            json={"adjustment": 5},
            headers=auth_headers(viewer_user),
        )

        assert resp.status_code == 403

    def test_viewer_cannot_create_inventory(
        self, client, viewer_user, warehouse, product
    ):
        resp = client.post(
            "/api/inventory",
            json={
                "warehouse_id": warehouse.id,
                "product_id": product.id,
                "quantity": 20,
            },
            headers=auth_headers(viewer_user),
        )

        assert resp.status_code == 403
