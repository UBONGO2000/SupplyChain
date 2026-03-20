"""
API Routers Package
===================
Organizes endpoints into domain-specific modules.
"""

from routers.auth import router as auth_router
from routers.warehouses import router as warehouses_router
from routers.suppliers import router as suppliers_router
from routers.products import router as products_router
from routers.inventory import router as inventory_router
from routers.shipments import router as shipments_router
from routers.orders import router as orders_router
from routers.analytics import router as analytics_router

__all__ = [
    "auth_router",
    "warehouses_router",
    "suppliers_router",
    "products_router",
    "inventory_router",
    "shipments_router",
    "orders_router",
    "analytics_router",
]
