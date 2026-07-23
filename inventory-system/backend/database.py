"""
Database setup + SQLAlchemy models.
Uses SQLite by default (zero-config, file-based) -- good enough for a single
shop. If the shop grows / wants multi-branch, swap DATABASE_URL for a
postgres connection string and nothing else needs to change.
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./inventory.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "admin" or "employee"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="employee")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    qr_code_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, default="General")
    price = Column(Float, nullable=False)
    cost_price = Column(Float, default=0.0)
    quantity = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=5)
    commission_enabled = Column(Boolean, default=False)
    commission_type = Column(String, default="percent")  # "percent" or "flat"
    commission_value = Column(Float, default=0.0)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("TransactionItem", back_populates="product")
    stock_logs = relationship("StockLog", back_populates="product")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"))
    customer_name = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    total_amount = Column(Float, default=0.0)
    total_commission = Column(Float, default=0.0)
    payment_method = Column(String, default="cash")  # cash / upi / card / other
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("User", back_populates="transactions")
    items = relationship("TransactionItem", back_populates="transaction", cascade="all, delete-orphan")


class TransactionItem(Base):
    __tablename__ = "transaction_items"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    product_name_snapshot = Column(String)
    quantity = Column(Integer, default=1)
    price_at_sale = Column(Float, nullable=False)
    original_price = Column(Float, nullable=False)
    commission_earned = Column(Float, default=0.0)

    transaction = relationship("Transaction", back_populates="items")
    product = relationship("Product", back_populates="items")


class StockLog(Base):
    """Audit trail for every stock change -- sale, correction, or restock."""
    __tablename__ = "stock_logs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    change = Column(Integer, nullable=False)  # negative = reduced, positive = added
    reason = Column(String, nullable=False)  # "sale", "restock", "correction", "damage"
    note = Column(Text, default="")
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="stock_logs")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
