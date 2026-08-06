"""
Demo Data Seeding
==================
Populates the database with realistic demo data so the API is immediately
testable (by recruiters, a future Angular frontend, or Postman) instead of
returning empty lists on every endpoint.

Idempotent by design: safe to call on every deploy/startup, it only inserts
data the first time (checked via the absence of any Warehouse row).
"""

from datetime import datetime, timedelta

import models
from database import SessionLocal


def seed_demo_data() -> None:
    """Insert demo warehouses, suppliers, products, inventory, shipments
    and orders if the database is empty. No-op otherwise."""
    db = SessionLocal()
    try:
        if db.query(models.Warehouse).first():
            print("Seed: demo data already present, skipping.")
            return

        print("Seed: populating demo data...")

        # ---------------------------------------------------------
        # Warehouses
        # ---------------------------------------------------------
        warehouses = [
            models.Warehouse(
                name="Entrepot Paris Nord",
                location="Paris",
                address="12 Rue de la Logistique, 93200 Saint-Denis",
                capacity_m3=8000,
                current_utilization=45.00,
            ),
            models.Warehouse(
                name="Entrepot Lyon Sud",
                location="Lyon",
                address="45 Avenue des Transporteurs, 69800 Saint-Priest",
                capacity_m3=5000,
                current_utilization=60.00,
            ),
            models.Warehouse(
                name="Entrepot Toulouse Ouest",
                location="Toulouse",
                address="8 Impasse des Fournisseurs, 31700 Blagnac",
                capacity_m3=3000,
                current_utilization=30.00,
            ),
        ]
        db.add_all(warehouses)
        db.flush()  # get IDs without committing yet

        # ---------------------------------------------------------
        # Suppliers
        # ---------------------------------------------------------
        suppliers = [
            models.Supplier(
                company_name="TechSupply France",
                contact_name="Julien Marchand",
                contact_email="contact@techsupply.fr",
                contact_phone="+33 1 42 00 00 01",
                country="France",
                rating=4.80,
                total_orders=32,
                on_time_delivery_rate=96.50,
            ),
            models.Supplier(
                company_name="Global Textiles Ltd",
                contact_name="Amara Okafor",
                contact_email="sales@globaltextiles.co.uk",
                contact_phone="+44 20 7946 0021",
                country="United Kingdom",
                rating=4.20,
                total_orders=18,
                on_time_delivery_rate=91.00,
            ),
            models.Supplier(
                company_name="AgroFresh Distribution",
                contact_name="Marie Dubois",
                contact_email="contact@agrofresh.be",
                contact_phone="+32 2 555 01 23",
                country="Belgium",
                rating=4.60,
                total_orders=25,
                on_time_delivery_rate=94.00,
            ),
            models.Supplier(
                company_name="Industria Componentes",
                contact_name="Carlos Ruiz",
                contact_email="ventas@industriacomponentes.es",
                contact_phone="+34 91 123 45 67",
                country="Spain",
                rating=4.00,
                total_orders=12,
                on_time_delivery_rate=88.00,
            ),
        ]
        db.add_all(suppliers)
        db.flush()

        tech, textile, agro, indus = suppliers

        # ---------------------------------------------------------
        # Products
        # ---------------------------------------------------------
        products = [
            models.Product(
                sku="ELEC-001", name="Clavier mecanique RGB",
                description="Clavier mecanique retroeclaire, switches rouges",
                category=models.ProductCategory.ELECTRONICS,
                unit_price=79.99, weight_kg=1.100, dimensions_cm="44x14x4",
                reorder_point=15, reorder_quantity=50, supplier_id=tech.id,
            ),
            models.Product(
                sku="ELEC-002", name="Ecran 27 pouces 4K",
                description="Moniteur IPS 4K 60Hz, USB-C",
                category=models.ProductCategory.ELECTRONICS,
                unit_price=349.00, weight_kg=5.400, dimensions_cm="62x40x8",
                reorder_point=8, reorder_quantity=20, supplier_id=tech.id,
            ),
            models.Product(
                sku="ELEC-003", name="Casque audio sans fil",
                description="Casque Bluetooth a reduction de bruit active",
                category=models.ProductCategory.ELECTRONICS,
                unit_price=129.90, weight_kg=0.280, dimensions_cm="20x18x8",
                reorder_point=20, reorder_quantity=60, supplier_id=tech.id,
            ),
            models.Product(
                sku="ELEC-004", name="Chargeur USB-C 65W",
                description="Chargeur rapide compatible laptop/telephone",
                category=models.ProductCategory.ELECTRONICS,
                unit_price=24.99, weight_kg=0.150, dimensions_cm="6x6x3",
                reorder_point=30, reorder_quantity=100, supplier_id=tech.id,
            ),
            models.Product(
                sku="TEXT-001", name="T-shirt coton bio",
                description="T-shirt unisexe, coton biologique certifie",
                category=models.ProductCategory.TEXTILE,
                unit_price=14.50, weight_kg=0.180, dimensions_cm="30x20x2",
                reorder_point=50, reorder_quantity=200, supplier_id=textile.id,
            ),
            models.Product(
                sku="TEXT-002", name="Veste impermeable",
                description="Veste coupe-vent et impermeable, capuche",
                category=models.ProductCategory.TEXTILE,
                unit_price=89.00, weight_kg=0.650, dimensions_cm="40x30x5",
                reorder_point=15, reorder_quantity=40, supplier_id=textile.id,
            ),
            models.Product(
                sku="FOOD-001", name="Cafe en grains 1kg",
                description="Cafe arabica torrefaction artisanale",
                category=models.ProductCategory.FOOD,
                unit_price=12.90, weight_kg=1.000, dimensions_cm="20x10x10",
                reorder_point=40, reorder_quantity=150, supplier_id=agro.id,
            ),
            models.Product(
                sku="FOOD-002", name="Huile d'olive extra vierge 500ml",
                description="Huile d'olive premiere pression a froid",
                category=models.ProductCategory.FOOD,
                unit_price=8.50, weight_kg=0.550, dimensions_cm="25x8x8",
                reorder_point=35, reorder_quantity=120, supplier_id=agro.id,
            ),
            models.Product(
                sku="IND-001", name="Roulement a billes 20mm",
                description="Roulement a billes standard, usage industriel",
                category=models.ProductCategory.INDUSTRIAL,
                unit_price=4.25, weight_kg=0.090, dimensions_cm="4x4x2",
                reorder_point=100, reorder_quantity=500, supplier_id=indus.id,
            ),
            models.Product(
                sku="IND-002", name="Moteur electrique 1.5kW",
                description="Moteur triphase pour applications industrielles",
                category=models.ProductCategory.INDUSTRIAL,
                unit_price=245.00, weight_kg=18.000, dimensions_cm="35x25x25",
                reorder_point=5, reorder_quantity=15, supplier_id=indus.id,
            ),
        ]
        db.add_all(products)
        db.flush()

        wh_paris, wh_lyon, wh_toulouse = warehouses
        p = {prod.sku: prod for prod in products}

        # ---------------------------------------------------------
        # Inventory (stock levels per warehouse/product)
        # Deliberately includes a couple of low-stock rows so the
        # /api/analytics/low-stock-alerts endpoint has something to show.
        # ---------------------------------------------------------
        inventory_rows = [
            models.Inventory(warehouse_id=wh_paris.id, product_id=p["ELEC-001"].id,
                              quantity=120, reserved_quantity=10, available_quantity=110,
                              reorder_level=15, max_stock_level=300, location_in_warehouse="A1-03"),
            models.Inventory(warehouse_id=wh_paris.id, product_id=p["ELEC-002"].id,
                              quantity=18, reserved_quantity=2, available_quantity=16,
                              reorder_level=8, max_stock_level=60, location_in_warehouse="A2-01"),
            models.Inventory(warehouse_id=wh_paris.id, product_id=p["ELEC-004"].id,
                              quantity=200, reserved_quantity=15, available_quantity=185,
                              reorder_level=30, max_stock_level=500, location_in_warehouse="A1-07"),
            models.Inventory(warehouse_id=wh_lyon.id, product_id=p["TEXT-001"].id,
                              quantity=340, reserved_quantity=20, available_quantity=320,
                              reorder_level=50, max_stock_level=800, location_in_warehouse="B3-02"),
            models.Inventory(warehouse_id=wh_lyon.id, product_id=p["TEXT-002"].id,
                              quantity=12, reserved_quantity=0, available_quantity=12,
                              reorder_level=15, max_stock_level=100, location_in_warehouse="B3-05"),
            models.Inventory(warehouse_id=wh_lyon.id, product_id=p["FOOD-001"].id,
                              quantity=210, reserved_quantity=30, available_quantity=180,
                              reorder_level=40, max_stock_level=600, location_in_warehouse="C1-01"),
            models.Inventory(warehouse_id=wh_toulouse.id, product_id=p["FOOD-002"].id,
                              quantity=150, reserved_quantity=10, available_quantity=140,
                              reorder_level=35, max_stock_level=400, location_in_warehouse="C2-04"),
            models.Inventory(warehouse_id=wh_toulouse.id, product_id=p["IND-001"].id,
                              quantity=40, reserved_quantity=0, available_quantity=40,
                              reorder_level=100, max_stock_level=1000, location_in_warehouse="D1-01"),  # low stock
            models.Inventory(warehouse_id=wh_toulouse.id, product_id=p["IND-002"].id,
                              quantity=3, reserved_quantity=1, available_quantity=2,
                              reorder_level=5, max_stock_level=30, location_in_warehouse="D2-01"),  # low stock
            models.Inventory(warehouse_id=wh_paris.id, product_id=p["ELEC-003"].id,
                              quantity=75, reserved_quantity=5, available_quantity=70,
                              reorder_level=20, max_stock_level=200, location_in_warehouse="A2-06"),
        ]
        db.add_all(inventory_rows)

        # ---------------------------------------------------------
        # Shipments
        # ---------------------------------------------------------
        now = datetime.utcnow()
        shipments = [
            models.Shipment(
                tracking_number="SHP-2026-0001",
                origin_warehouse_id=wh_paris.id, supplier_id=tech.id,
                destination_address="Client Pro - 5 Rue du Commerce, 75015 Paris",
                status=models.ShipmentStatus.DELIVERED,
                departure_date=now - timedelta(days=10),
                arrival_date=now - timedelta(days=6),
                actual_arrival_date=now - timedelta(days=6),
                total_cost=145.00, shipping_method="Ground", carrier_name="Chronopost",
            ),
            models.Shipment(
                tracking_number="SHP-2026-0002",
                origin_warehouse_id=wh_lyon.id, supplier_id=textile.id,
                destination_address="Boutique Textile - 3 Place Bellecour, 69002 Lyon",
                status=models.ShipmentStatus.IN_TRANSIT,
                departure_date=now - timedelta(days=2),
                arrival_date=now + timedelta(days=1),
                total_cost=89.50, shipping_method="Ground", carrier_name="DHL",
            ),
            models.Shipment(
                tracking_number="SHP-2026-0003",
                origin_warehouse_id=wh_toulouse.id, supplier_id=indus.id,
                destination_address="Usine Sud - Zone Industrielle, 31200 Toulouse",
                status=models.ShipmentStatus.PENDING,
                departure_date=now + timedelta(days=1),
                arrival_date=now + timedelta(days=4),
                total_cost=310.00, shipping_method="Air", carrier_name="FedEx",
            ),
        ]
        db.add_all(shipments)

        # ---------------------------------------------------------
        # Orders + OrderItems
        # (attach to the seeded default users created by create_default_users)
        # ---------------------------------------------------------
        admin_user = db.query(models.User).filter(models.User.username == "admin").first()
        staff_user = db.query(models.User).filter(models.User.username == "staff").first()

        if admin_user:
            order1 = models.Order(
                order_number="ORD-2026-0001",
                user_id=admin_user.id,
                status=models.OrderStatus.DELIVERED,
                subtotal=239.79, tax_amount=23.98, shipping_cost=9.90, total_amount=273.67,
                shipping_address="Client Pro - 5 Rue du Commerce, 75015 Paris",
                ordered_at=now - timedelta(days=12),
                shipped_at=now - timedelta(days=10),
                delivered_at=now - timedelta(days=6),
            )
            db.add(order1)
            db.flush()
            db.add_all([
                models.OrderItem(order_id=order1.id, product_id=p["ELEC-001"].id,
                                  quantity=2, unit_price=79.99, discount_percent=0,
                                  line_total=159.98),
                models.OrderItem(order_id=order1.id, product_id=p["ELEC-004"].id,
                                  quantity=1, unit_price=24.99, discount_percent=0,
                                  line_total=24.99),
                models.OrderItem(order_id=order1.id, product_id=p["ELEC-003"].id,
                                  quantity=1, unit_price=129.90, discount_percent=15,
                                  line_total=110.42),
            ])

        if staff_user:
            order2 = models.Order(
                order_number="ORD-2026-0002",
                user_id=staff_user.id,
                status=models.OrderStatus.PROCESSING,
                subtotal=178.00, tax_amount=17.80, shipping_cost=5.90, total_amount=201.70,
                shipping_address="Boutique Textile - 3 Place Bellecour, 69002 Lyon",
                ordered_at=now - timedelta(days=1),
            )
            db.add(order2)
            db.flush()
            db.add_all([
                models.OrderItem(order_id=order2.id, product_id=p["TEXT-002"].id,
                                  quantity=2, unit_price=89.00, discount_percent=0,
                                  line_total=178.00),
            ])

        db.commit()
        print("Seed: demo data created successfully "
              f"({len(warehouses)} warehouses, {len(suppliers)} suppliers, "
              f"{len(products)} products, {len(inventory_rows)} inventory rows, "
              f"{len(shipments)} shipments, 2 orders).")

    except Exception as e:
        db.rollback()
        print(f"Seed: failed to create demo data: {e}")
        raise
    finally:
        db.close()