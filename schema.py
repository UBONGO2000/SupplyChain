"""
Pydantic Schemas (Data Validation Models)
==========================================
Request/Response models for the Supply Chain API.

Purpose:
- Validate incoming request data
- Serialize outgoing response data
- Document API data structures with type hints
- Enforce business rules through validation

Schemas follow a pattern:
- Base: Common fields for creation
- Create: Fields required for new resources
- Update: Fields for partial updates (all optional)
- Response: Complete fields including generated/IDs
- List: Paginated response wrapper
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum


# ============================================
# Enums (must match models.py)
# ============================================
class UserRoleEnum(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"
    VIEWER = "viewer"


class ProductCategoryEnum(str, Enum):
    ELECTRONICS = "Electronics"
    FOOD = "Food"
    TEXTILE = "Textile"
    INDUSTRIAL = "Industrial"


class ShipmentStatusEnum(str, Enum):
    PENDING = "Pending"
    IN_TRANSIT = "In Transit"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"


class OrderStatusEnum(str, Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    SHIPPED = "Shipped"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"


# ============================================
# Utility Schemas
# ============================================
class PaginationParams(BaseModel):
    """Standard pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number (starts at 1)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseModel):
    """Standard paginated response wrapper"""
    items: List
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @classmethod
    def create(cls, items: List, total: int, page: int, page_size: int):
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


class MessageResponse(BaseModel):
    """Standard message response"""
    message: str
    success: bool = True


# ============================================
# USER SCHEMAS
# ============================================
class UserBase(BaseModel):
    """Base fields for user operations"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=200)
    role: UserRoleEnum = UserRoleEnum.STAFF


class UserCreate(UserBase):
    """Fields required to create a new user"""
    password: str = Field(..., min_length=8, max_length=100)
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Ensure password meets complexity requirements"""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    """Fields for updating a user (all optional)"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=200)
    role: Optional[UserRoleEnum] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)


class UserResponse(UserBase):
    """User response (excludes password)"""
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Login request"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# ============================================
# WAREHOUSE SCHEMAS
# ============================================
class WarehouseBase(BaseModel):
    """Base fields for warehouse"""
    name: str = Field(..., min_length=1, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    capacity_m3: Optional[Decimal] = Field(None, ge=0)
    current_utilization: Optional[Decimal] = Field(None, ge=0, le=100)


class WarehouseCreate(WarehouseBase):
    """Fields required to create warehouse"""
    is_active: bool = True


class WarehouseUpdate(BaseModel):
    """Fields for updating warehouse"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    capacity_m3: Optional[Decimal] = Field(None, ge=0)
    current_utilization: Optional[Decimal] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None


class WarehouseResponse(WarehouseBase):
    """Full warehouse response"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================
# SUPPLIER SCHEMAS
# ============================================
class SupplierBase(BaseModel):
    """Base fields for supplier"""
    company_name: str = Field(..., min_length=1, max_length=150)
    contact_name: Optional[str] = Field(None, max_length=200)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    country: Optional[str] = Field(None, max_length=50)
    rating: Decimal = Field(default=5.00, ge=0, le=5.00)
    on_time_delivery_rate: Decimal = Field(default=100.00, ge=0, le=100.00)


class SupplierCreate(SupplierBase):
    """Fields required to create supplier"""
    is_active: bool = True


class SupplierUpdate(BaseModel):
    """Fields for updating supplier"""
    company_name: Optional[str] = Field(None, min_length=1, max_length=150)
    contact_name: Optional[str] = Field(None, max_length=200)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    country: Optional[str] = Field(None, max_length=50)
    rating: Optional[Decimal] = Field(None, ge=0, le=5.00)
    on_time_delivery_rate: Optional[Decimal] = Field(None, ge=0, le=100.00)
    is_active: Optional[bool] = None


class SupplierResponse(SupplierBase):
    """Full supplier response"""
    id: int
    total_orders: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================
# PRODUCT SCHEMAS
# ============================================
class ProductBase(BaseModel):
    """Base fields for product"""
    sku: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: ProductCategoryEnum
    unit_price: Decimal = Field(..., ge=0)
    weight_kg: Optional[Decimal] = Field(None, ge=0)
    dimensions_cm: Optional[str] = Field(None, max_length=50)
    reorder_point: int = Field(default=0, ge=0)
    reorder_quantity: int = Field(default=0, ge=0)
    supplier_id: Optional[int] = None


class ProductCreate(ProductBase):
    """Fields required to create product"""
    is_active: bool = True


class ProductUpdate(BaseModel):
    """Fields for updating product"""
    sku: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[ProductCategoryEnum] = None
    unit_price: Optional[Decimal] = Field(None, ge=0)
    weight_kg: Optional[Decimal] = Field(None, ge=0)
    dimensions_cm: Optional[str] = Field(None, max_length=50)
    reorder_point: Optional[int] = Field(None, ge=0)
    reorder_quantity: Optional[int] = Field(None, ge=0)
    supplier_id: Optional[int] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    """Full product response"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProductWithInventoryResponse(ProductResponse):
    """Product with inventory summary"""
    total_quantity: int = 0
    available_quantity: int = 0
    warehouses_count: int = 0


# ============================================
# INVENTORY SCHEMAS
# ============================================
class InventoryBase(BaseModel):
    """Base fields for inventory"""
    warehouse_id: int
    product_id: int
    quantity: int = Field(default=0, ge=0)
    reserved_quantity: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=10, ge=0)
    max_stock_level: Optional[int] = Field(None, ge=0)
    location_in_warehouse: Optional[str] = Field(None, max_length=50)


class InventoryCreate(InventoryBase):
    """Fields required to create inventory record"""
    pass


class InventoryUpdate(BaseModel):
    """Fields for updating inventory"""
    quantity: Optional[int] = Field(None, ge=0)
    reserved_quantity: Optional[int] = Field(None, ge=0)
    reorder_level: Optional[int] = Field(None, ge=0)
    max_stock_level: Optional[int] = Field(None, ge=0)
    location_in_warehouse: Optional[str] = Field(None, max_length=50)


class InventoryResponse(InventoryBase):
    """Full inventory response"""
    available_quantity: int
    last_updated: datetime
    
    class Config:
        from_attributes = True


class InventoryAdjustRequest(BaseModel):
    """Request to adjust inventory quantity"""
    adjustment: int = Field(..., description="Positive for additions, negative for deductions")
    reason: Optional[str] = Field(None, max_length=500)


# ============================================
# SHIPMENT SCHEMAS
# ============================================
class ShipmentBase(BaseModel):
    """Base fields for shipment"""
    tracking_number: Optional[str] = Field(None, max_length=100)
    origin_warehouse_id: int
    supplier_id: Optional[int] = None
    destination_address: Optional[str] = None
    status: ShipmentStatusEnum = ShipmentStatusEnum.PENDING
    departure_date: Optional[datetime] = None
    arrival_date: Optional[datetime] = None
    total_cost: Optional[Decimal] = Field(None, ge=0)
    shipping_method: Optional[str] = Field(None, max_length=50)
    carrier_name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class ShipmentCreate(ShipmentBase):
    """Fields required to create shipment"""
    pass


class ShipmentUpdate(BaseModel):
    """Fields for updating shipment"""
    tracking_number: Optional[str] = Field(None, max_length=100)
    origin_warehouse_id: Optional[int] = None
    supplier_id: Optional[int] = None
    destination_address: Optional[str] = None
    status: Optional[ShipmentStatusEnum] = None
    departure_date: Optional[datetime] = None
    arrival_date: Optional[datetime] = None
    actual_arrival_date: Optional[datetime] = None
    total_cost: Optional[Decimal] = Field(None, ge=0)
    shipping_method: Optional[str] = Field(None, max_length=50)
    carrier_name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class ShipmentResponse(ShipmentBase):
    """Full shipment response"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================
# ORDER SCHEMAS
# ============================================
class OrderItemBase(BaseModel):
    """Base fields for order item"""
    product_id: int
    quantity: int = Field(..., ge=1)
    unit_price: Decimal = Field(..., ge=0)
    discount_percent: Decimal = Field(default=0.00, ge=0, le=100)


class OrderItemCreate(OrderItemBase):
    """Fields required to create order item"""
    pass


class OrderItemResponse(OrderItemBase):
    """Full order item response"""
    id: int
    line_total: Decimal
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    """Base fields for order"""
    shipping_address: Optional[str] = None
    billing_address: Optional[str] = None
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    """Fields required to create order"""
    user_id: int
    items: List[OrderItemCreate] = Field(..., min_length=1)
    
    @field_validator('items')
    @classmethod
    def validate_items_not_empty(cls, v: List) -> List:
        if not v:
            raise ValueError('At least one item is required')
        return v


class OrderUpdate(BaseModel):
    """Fields for updating order"""
    status: Optional[OrderStatusEnum] = None
    shipping_address: Optional[str] = None
    billing_address: Optional[str] = None
    notes: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None


class OrderResponse(OrderBase):
    """Full order response"""
    id: int
    order_number: str
    user_id: int
    status: OrderStatusEnum
    subtotal: Decimal
    tax_amount: Decimal
    shipping_cost: Decimal
    total_amount: Decimal
    ordered_at: datetime
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    order_items: List[OrderItemResponse] = []
    
    class Config:
        from_attributes = True


# ============================================
# ANALYTICS / REPORTING SCHEMAS
# ============================================
class InventorySummary(BaseModel):
    """Inventory summary by warehouse"""
    warehouse_id: int
    warehouse_name: str
    total_products: int
    total_quantity: int
    total_value: Decimal
    utilization_percent: Decimal


class SalesSummary(BaseModel):
    """Sales summary report"""
    total_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    orders_by_status: dict


class LowStockAlert(BaseModel):
    """Low stock product alert"""
    product_id: int
    product_name: str
    sku: str
    warehouse_id: int
    warehouse_name: str
    current_quantity: int
    reorder_level: int
