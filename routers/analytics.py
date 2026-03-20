"""
Analytics Router
================
Reporting and analytics endpoints with complex SQL queries.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

import models
from schema import InventorySummary, SalesSummary, LowStockAlert
from auth import get_current_user, require_role
from database import get_db

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/inventory-summary", response_model=List[InventorySummary])
def get_inventory_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get inventory summary by warehouse.
    Shows total products, quantities, and value per warehouse using SQL aggregation with JOINs.
    """
    results = db.query(
        models.Warehouse.id,
        models.Warehouse.name,
        func.count(models.Inventory.product_id).label("total_products"),
        func.sum(models.Inventory.quantity).label("total_quantity"),
        func.sum(models.Inventory.quantity * models.Product.unit_price).label("total_value"),
        models.Warehouse.capacity_m3,
        models.Warehouse.current_utilization,
    ).join(
        models.Inventory, models.Warehouse.id == models.Inventory.warehouse_id
    ).join(
        models.Product, models.Inventory.product_id == models.Product.id
    ).group_by(
        models.Warehouse.id
    ).all()

    return [
        InventorySummary(
            warehouse_id=r.id,
            warehouse_name=r.name,
            total_products=r.total_products or 0,
            total_quantity=r.total_quantity or 0,
            total_value=r.total_value or Decimal("0.00"),
            utilization_percent=r.current_utilization or Decimal("0.00"),
        )
        for r in results
    ]


@router.get("/sales-summary", response_model=SalesSummary)
def get_sales_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"])),
):
    """
    Get sales summary with date range filtering.
    Uses complex aggregation queries for total orders, revenue, and average order value.
    """
    query = db.query(models.Order)

    if start_date:
        query = query.filter(models.Order.ordered_at >= start_date)
    if end_date:
        query = query.filter(models.Order.ordered_at <= end_date)

    total_orders = query.count()
    total_revenue = query.with_entities(func.sum(models.Order.total_amount)).scalar() or Decimal("0")

    avg_order_value = Decimal("0") if total_orders == 0 else total_revenue / total_orders

    status_counts = db.query(
        models.Order.status,
        func.count(models.Order.id)
    ).group_by(models.Order.status).all()

    orders_by_status = {status.value: count for status, count in status_counts}

    return SalesSummary(
        total_orders=total_orders,
        total_revenue=total_revenue,
        average_order_value=avg_order_value,
        orders_by_status=orders_by_status,
    )


@router.get("/low-stock-alerts", response_model=List[LowStockAlert])
def get_low_stock_alerts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get all products below reorder point.
    Uses subquery to find products needing reorder.
    """
    results = db.query(
        models.Product.id.label("product_id"),
        models.Product.name.label("product_name"),
        models.Product.sku.label("sku"),
        models.Inventory.warehouse_id.label("warehouse_id"),
        models.Warehouse.name.label("warehouse_name"),
        models.Inventory.quantity.label("quantity"),
        models.Inventory.reorder_level.label("reorder_level"),
    ).join(
        models.Inventory, models.Product.id == models.Inventory.product_id
    ).join(
        models.Warehouse, models.Inventory.warehouse_id == models.Warehouse.id
    ).filter(
        models.Inventory.quantity < models.Inventory.reorder_level
    ).all()

    return [
        LowStockAlert(
            product_id=r.product_id,
            product_name=r.product_name,
            sku=r.sku,
            warehouse_id=r.warehouse_id,
            warehouse_name=r.warehouse_name,
            current_quantity=r.quantity,
            reorder_level=r.reorder_level,
        )
        for r in results
    ]


@router.get("/top-products")
def get_top_products(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get top selling products by order quantity. Uses complex join and aggregation."""
    results = db.query(
        models.Product.id,
        models.Product.name,
        models.Product.sku,
        models.Product.category,
        func.sum(models.OrderItem.quantity).label("total_sold"),
        func.count(models.OrderItem.order_id).label("order_count"),
    ).join(
        models.OrderItem, models.Product.id == models.OrderItem.product_id
    ).join(
        models.Order, models.OrderItem.order_id == models.Order.id
    ).group_by(
        models.Product.id
    ).order_by(
        desc("total_sold")
    ).limit(limit).all()

    return [
        {
            "product_id": r.id,
            "name": r.name,
            "sku": r.sku,
            "category": r.category.value,
            "total_sold": r.total_sold,
            "order_count": r.order_count,
        }
        for r in results
    ]


@router.get("/supplier-performance")
def get_supplier_performance(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["admin", "manager"])),
):
    """
    Get supplier performance metrics.
    Shows supplier ratings, on-time delivery, and order counts.
    """
    results = db.query(
        models.Supplier.id,
        models.Supplier.company_name,
        models.Supplier.country,
        models.Supplier.rating,
        models.Supplier.on_time_delivery_rate,
        func.count(models.Shipment.id).label("shipment_count"),
    ).outerjoin(
        models.Shipment, models.Supplier.id == models.Shipment.supplier_id
    ).group_by(
        models.Supplier.id
    ).order_by(
        desc(models.Supplier.rating)
    ).all()

    return [
        {
            "supplier_id": r.id,
            "company_name": r.company_name,
            "country": r.country,
            "rating": float(r.rating),
            "on_time_delivery_rate": float(r.on_time_delivery_rate),
            "shipment_count": r.shipment_count,
        }
        for r in results
    ]
