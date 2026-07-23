from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ---------- Auth ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    user_id: int


# ---------- Users ----------
class UserCreate(BaseModel):
    name: str
    username: str
    password: str
    role: str  # "admin" or "employee"


class UserOut(BaseModel):
    id: int
    name: str
    username: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


# ---------- Products ----------
class ProductCreate(BaseModel):
    name: str
    category: str = "General"
    price: float
    cost_price: float = 0.0
    quantity: int = 0
    low_stock_threshold: int = 5
    commission_enabled: bool = False
    commission_type: str = "percent"  # "percent" or "flat"
    commission_value: float = 0.0
    notes: str = ""


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    cost_price: Optional[float] = None
    low_stock_threshold: Optional[int] = None
    commission_enabled: Optional[bool] = None
    commission_type: Optional[str] = None
    commission_value: Optional[float] = None
    notes: Optional[str] = None


class ProductOut(BaseModel):
    id: int
    qr_code_id: str
    name: str
    category: str
    price: float
    cost_price: float
    quantity: int
    low_stock_threshold: int
    commission_enabled: bool
    commission_type: str
    commission_value: float
    notes: str

    class Config:
        from_attributes = True


class StockAdjust(BaseModel):
    change: int  # positive to add stock, negative to remove
    reason: str  # "restock", "correction", "damage"
    note: str = ""


# ---------- Billing ----------
class CartItem(BaseModel):
    product_id: int
    quantity: int
    price_override: Optional[float] = None  # editable price (discount) at billing time


class CheckoutRequest(BaseModel):
    items: List[CartItem]
    payment_method: str  # cash / upi / card / other
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None


class TransactionItemOut(BaseModel):
    product_name_snapshot: str
    quantity: int
    price_at_sale: float
    original_price: float
    commission_earned: float

    class Config:
        from_attributes = True


class TransactionOut(BaseModel):
    id: int
    employee_id: int
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    total_amount: float
    total_commission: float
    payment_method: str
    created_at: datetime
    items: List[TransactionItemOut]

    class Config:
        from_attributes = True


class EmployeeProfileOut(BaseModel):
    id: int
    name: str
    username: str
    is_active: bool
    today_sales: float
    today_commission: float
    today_bills: int
    month_sales: float
    month_commission: float
    month_bills: int


class DailySalesEntry(BaseModel):
    date: str
    sales: float
    commission: float
    bills: int

