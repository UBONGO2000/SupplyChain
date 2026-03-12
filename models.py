"""
SQLAlchemy ORM Models
======================
Database models for the Supply Chain Management System.

Models:
- User: Authentication and authorization
- Warehouse: Storage facilities
- Supplier: Vendor management
- Product: Product catalog
- Inventory: Stock tracking (junction table)
- Shipment: Shipping/fulfillment tracking
- Order: Customer orders
- OrderItem: Individual line items in orders

Relationships:
- User 1→N Order
- Warehouse 1→N Inventory
- Product 1→N Inventory
- Supplier 1→N Shipment
- Warehouse 1→N Shipment
- Order 1→N OrderItem
- Product 1→N OrderItem
"""

from sqlalchemy import (
    Column, Integer, String, DECIMAL, Enum, TIMESTAMP, 
    ForeignKey, Text, Boolean, Index, func
)
from sqlalchemy.orm import relationship, backref
from database import Base
from enum import Enum as PyEnum


# ============================================
# Enums for Type Safety
# ============================================
class UserRole(PyEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"
    VIEWER = "viewer"


class ProductCategory(PyEnum):
    ELECTRONICS = "Electronics"
    FOOD = "Food"
    TEXTILE = "Textile"
    INDUSTRIAL = "Industrial"


class ShipmentStatus(PyEnum):
    PENDING = "Pending"
    IN_TRANSIT = "In Transit"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"


class OrderStatus(PyEnum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    SHIPPED = "Shipped"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"


# ============================================
# User Model - Authentication & Authorization
# ============================================
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200))
    role = Column(Enum(UserRole), default=UserRole.STAFF, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    orders = relationship("Order", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role.value}')>"


# ============================================
# Warehouse Model - Storage Facilities
# ============================================
class Warehouse(Base):
    __tablename__ = "warehouses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    location = Column(String(255))
    address = Column(Text)
    capacity_m3 = Column(DECIMAL(10, 2))
    current_utilization = Column(DECIMAL(5, 2), default=0.00)  # Percentage
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    inventory = relationship("Inventory", back_populates="warehouse", cascade="all, delete-orphan")
    outbound_shipments = relationship(
        "Shipment", 
        foreign_keys="Shipment.origin_warehouse_id",
        back_populates="origin_warehouse"
    )
    
    # Table args for indexes
    __table_args__ = (
        Index('idx_warehouse_location', 'location'),
        Index('idx_warehouse_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Warehouse(id={self.id}, name='{self.name}', location='{self.location}')>"


# ============================================
# Supplier Model - Vendor Management
# ============================================
class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(150), nullable=False, index=True)
    contact_name = Column(String(200))
    contact_email = Column(String(100))
    contact_phone = Column(String(50))
    address = Column(Text)
    country = Column(String(50), index=True)
    rating = Column(DECIMAL(3, 2), default=5.00)
    total_orders = Column(Integer, default=0)
    on_time_delivery_rate = Column(DECIMAL(5, 2), default=100.00)  # Percentage
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    shipments = relationship("Shipment", back_populates="supplier")
    products = relationship("Product", back_populates="supplier")
    
    # Table args for indexes
    __table_args__ = (
        Index('idx_supplier_country', 'country'),
        Index('idx_supplier_rating', 'rating'),
    )
    
    def __repr__(self):
        return f"<Supplier(id={self.id}, company='{self.company_name}', country='{self.country}')>"


# ============================================
# Product Model - Product Catalog
# ============================================
class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    category = Column(Enum(ProductCategory), nullable=False, index=True)
    unit_price = Column(DECIMAL(12, 2), nullable=False)
    weight_kg = Column(DECIMAL(8, 3))
    dimensions_cm = Column(String(50))  # LxWxH format
    reorder_point = Column(Integer, default=0)  # Auto-reorder threshold
    reorder_quantity = Column(Integer, default=0)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    inventory = relationship("Inventory", back_populates="product", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="product")
    supplier = relationship("Supplier", back_populates="products")
    
    # Table args for indexes
    __table_args__ = (
        Index('idx_product_category', 'category'),
        Index('idx_product_supplier', 'supplier_id'),
        Index('idx_product_name', 'name'),
    )
    
    def __repr__(self):
        return f"<Product(id={self.id}, sku='{self.sku}', name='{self.name}', category='{self.category.value}')>"


# ============================================
# Inventory Model - Stock Tracking (Junction Table)
# ============================================
class Inventory(Base):
    __tablename__ = "inventory"
    
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0)  # Quantity reserved in orders
    available_quantity = Column(Integer, default=0)  # quantity - reserved_quantity
    reorder_level = Column(Integer, default=10)
    max_stock_level = Column(Integer)
    last_updated = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    location_in_warehouse = Column(String(50))  # Aisle-Shelf-Bin
    
    # Relationships
    warehouse = relationship("Warehouse", back_populates="inventory")
    product = relationship("Product", back_populates="inventory")
    
    # Table args for indexes
    __table_args__ = (
        Index('idx_inventory_product', 'product_id'),
        Index('idx_inventory_warehouse', 'warehouse_id'),
    )
    
    def __repr__(self):
        return f"<Inventory(warehouse_id={self.warehouse_id}, product_id={self.product_id}, qty={self.quantity})>"


# ============================================
# Shipment Model - Shipping/Receiving Tracking
# ============================================
class Shipment(Base):
    __tablename__ = "shipments"
    
    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String(100), unique=True, index=True)
    origin_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    destination_address = Column(Text)
    status = Column(Enum(ShipmentStatus), default=ShipmentStatus.PENDING, nullable=False, index=True)
    departure_date = Column(TIMESTAMP)
    arrival_date = Column(TIMESTAMP)
    actual_arrival_date = Column(TIMESTAMP)
    total_cost = Column(DECIMAL(15, 2))
    shipping_method = Column(String(50))  # Air, Sea, Ground
    carrier_name = Column(String(100))
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    origin_warehouse = relationship(
        "Warehouse", 
        foreign_keys=[origin_warehouse_id],
        back_populates="outbound_shipments"
    )
    supplier = relationship("Supplier", back_populates="shipments")
    
    # Table args for indexes
    __table_args__ = (
        Index('idx_shipment_status', 'status'),
        Index('idx_shipment_supplier', 'supplier_id'),
        Index('idx_shipment_dates', 'departure_date', 'arrival_date'),
    )
    
    def __repr__(self):
        return f"<Shipment(id={self.id}, tracking='{self.tracking_number}', status='{self.status.value}')>"


# ============================================
# Order Model - Customer Orders
# ============================================
class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)
    subtotal = Column(DECIMAL(12, 2), nullable=False)
    tax_amount = Column(DECIMAL(12, 2), default=0.00)
    shipping_cost = Column(DECIMAL(12, 2), default=0.00)
    total_amount = Column(DECIMAL(12, 2), nullable=False)
    shipping_address = Column(Text)
    billing_address = Column(Text)
    notes = Column(Text)
    ordered_at = Column(TIMESTAMP, server_default=func.now())
    shipped_at = Column(TIMESTAMP)
    delivered_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    # Table args for indexes
    __table_args__ = (
        Index('idx_order_user', 'user_id'),
        Index('idx_order_status', 'status'),
        Index('idx_order_dates', 'ordered_at'),
    )
    
    def __repr__(self):
        return f"<Order(id={self.id}, order_number='{self.order_number}', status='{self.status.value}')>"


# ============================================
# OrderItem Model - Individual Line Items
# ============================================
class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(12, 2), nullable=False)  # Price at time of order
    discount_percent = Column(DECIMAL(5, 2), default=0.00)
    line_total = Column(DECIMAL(12, 2), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    
    # Table args for indexes
    __table_args__ = (
        Index('idx_orderitem_order', 'order_id'),
        Index('idx_orderitem_product', 'product_id'),
    )
    
    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, product_id={self.product_id}, qty={self.quantity})>"
