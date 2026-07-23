"""
Inventory + Billing System -- main FastAPI app.

Run with:  uvicorn main:app --reload --host 0.0.0.0 --port 8000
Then open  http://localhost:8000  in a browser (any device on the same
network can use http://<your-computer-ip>:8000 instead of localhost).
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import os

from database import init_db, get_db, User, Product, Transaction, TransactionItem, StockLog
from auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_admin,
)
from qr_utils import generate_qr_id, generate_qr_image_bytes
from pdf_utils import generate_receipt_pdf
import schemas

SHOP_NAME = "Dukaan Manager"  # change this to your actual shop name


def require_self_or_admin(target_user_id: int, current_user: User):
    if current_user.role != "admin" and current_user.id != target_user_id:
        raise HTTPException(status_code=403, detail="You can only view your own data")

app = FastAPI(title="Inventory + Billing System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

# Seed a default admin account on first run so there's always a way in.
def seed_default_admin():
    from database import SessionLocal
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.role == "admin").first():
            admin = User(
                name="Owner",
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin",
            )
            db.add(admin)
            db.commit()
            print("Seeded default admin -> username: admin | password: admin123")
            print("IMPORTANT: change this password after first login.")
    finally:
        db.close()

seed_default_admin()


# ============================================================
# AUTH
# ============================================================
@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated")
    token = create_access_token({"sub": str(user.id)})
    return schemas.TokenResponse(
        access_token=token, role=user.role, name=user.name, user_id=user.id
    )


@app.get("/api/auth/me", response_model=schemas.UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# ============================================================
# USER MANAGEMENT (admin only) -- create employee logins
# ============================================================
@app.post("/api/users", response_model=schemas.UserOut)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="This username is already taken")
    if payload.role not in ("admin", "employee"):
        raise HTTPException(status_code=400, detail="Role must be admin or employee")
    user = User(
        name=payload.name,
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/api/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    return db.query(User).order_by(User.created_at.desc()).all()


@app.patch("/api/users/{user_id}/toggle-active", response_model=schemas.UserOut)
def toggle_user_active(user_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user


# ============================================================
# PRODUCTS (admin manages, everyone can read for scanning)
# ============================================================
@app.post("/api/products", response_model=schemas.ProductOut)
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    qr_id = generate_qr_id()
    while db.query(Product).filter(Product.qr_code_id == qr_id).first():
        qr_id = generate_qr_id()

    product = Product(qr_code_id=qr_id, **payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)

    if product.quantity != 0:
        db.add(StockLog(
            product_id=product.id, change=product.quantity,
            reason="initial_stock", note="Product create karte time initial stock"
        ))
        db.commit()
    return product


@app.get("/api/products", response_model=list[schemas.ProductOut])
def list_products(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Product).order_by(Product.name).all()


@app.get("/api/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.patch("/api/products/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, payload: schemas.ProductUpdate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"ok": True}


@app.get("/api/products/{product_id}/qr-image")
def get_qr_image(product_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    img_bytes = generate_qr_image_bytes(product.qr_code_id)
    return Response(content=img_bytes, media_type="image/png")


# Lookup by scanned QR text -- this is what the scanner hits
@app.get("/api/scan/{qr_code_id}", response_model=schemas.ProductOut)
def scan_lookup(qr_code_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.query(Product).filter(Product.qr_code_id == qr_code_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="This QR code doesn't match any product")
    return product


# ============================================================
# STOCK CORRECTIONS (admin only -- keeps an audit trail)
# ============================================================
@app.post("/api/products/{product_id}/stock-adjust", response_model=schemas.ProductOut)
def adjust_stock(product_id: int, payload: schemas.StockAdjust, db: Session = Depends(get_db), admin=Depends(require_admin)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    new_qty = product.quantity + payload.change
    if new_qty < 0:
        raise HTTPException(status_code=400, detail="Stock cannot go negative")
    product.quantity = new_qty
    db.add(StockLog(
        product_id=product.id, change=payload.change, reason=payload.reason,
        note=payload.note, performed_by=admin.id
    ))
    db.commit()
    db.refresh(product)
    return product


# ============================================================
# BILLING / CHECKOUT
# ============================================================
@app.post("/api/billing/checkout", response_model=schemas.TransactionOut)
def checkout(payload: schemas.CheckoutRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    if payload.payment_method not in ("cash", "upi", "card", "other"):
        raise HTTPException(status_code=400, detail="Invalid payment method")

    transaction = Transaction(
        employee_id=current_user.id,
        payment_method=payload.payment_method,
        customer_name=(payload.customer_name or None),
        customer_phone=(payload.customer_phone or None),
    )
    db.add(transaction)
    db.flush()  # get transaction.id before commit

    total_amount = 0.0
    total_commission = 0.0

    for item in payload.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product ID {item.product_id} not found")
        if item.quantity < 1:
            raise HTTPException(status_code=400, detail="Quantity must be at least 1")
        if product.quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"Not enough stock for '{product.name}' (available: {product.quantity})")

        sale_price = item.price_override if item.price_override is not None else product.price
        if sale_price < 0:
            raise HTTPException(status_code=400, detail="Price cannot be negative")

        line_total = sale_price * item.quantity

        commission = 0.0
        if product.commission_enabled:
            if product.commission_type == "percent":
                commission = (product.commission_value / 100.0) * line_total
            else:  # flat per unit
                commission = product.commission_value * item.quantity

        db.add(TransactionItem(
            transaction_id=transaction.id,
            product_id=product.id,
            product_name_snapshot=product.name,
            quantity=item.quantity,
            price_at_sale=sale_price,
            original_price=product.price,
            commission_earned=commission,
        ))

        product.quantity -= item.quantity
        db.add(StockLog(
            product_id=product.id, change=-item.quantity, reason="sale",
            note=f"Transaction #{transaction.id}", performed_by=current_user.id
        ))

        total_amount += line_total
        total_commission += commission

    transaction.total_amount = total_amount
    transaction.total_commission = total_commission
    db.commit()
    db.refresh(transaction)
    return transaction


@app.get("/api/billing/transactions", response_model=list[schemas.TransactionOut])
def list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 50,
):
    query = db.query(Transaction).order_by(Transaction.created_at.desc())
    # employees only see their own sales; admin sees everything
    if current_user.role != "admin":
        query = query.filter(Transaction.employee_id == current_user.id)
    return query.limit(limit).all()


@app.get("/api/billing/transactions/{transaction_id}", response_model=schemas.TransactionOut)
def get_transaction(transaction_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Bill not found")
    require_self_or_admin(txn.employee_id, current_user)
    return txn


@app.get("/api/billing/transactions/{transaction_id}/pdf")
def get_transaction_pdf(transaction_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Bill not found")
    require_self_or_admin(txn.employee_id, current_user)
    employee = db.query(User).filter(User.id == txn.employee_id).first()
    pdf_bytes = generate_receipt_pdf(SHOP_NAME, txn, employee.name if employee else "Staff")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="bill-{txn.id}.pdf"'},
    )


@app.get("/api/billing/transactions/{transaction_id}/whatsapp-link")
def get_whatsapp_link(transaction_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns a wa.me deep link with a pre-filled message summarizing the bill.
    NOTE: WhatsApp does not allow any third party to auto-send messages or
    attachments without the paid WhatsApp Business API. This link opens
    WhatsApp with the message ready -- the person just taps Send, and can
    attach the downloaded PDF manually if they want to share the full bill.
    """
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Bill not found")
    require_self_or_admin(txn.employee_id, current_user)
    if not txn.customer_phone:
        raise HTTPException(status_code=400, detail="No customer phone number saved for this bill")

    lines = [f"*{SHOP_NAME}* - Bill #{txn.id}", txn.created_at.strftime("%d %b %Y, %I:%M %p"), ""]
    for item in txn.items:
        lines.append(f"{item.product_name_snapshot} x{item.quantity} = Rs.{item.price_at_sale * item.quantity:.2f}")
    lines.append("")
    lines.append(f"Total: Rs.{txn.total_amount:.2f}")
    lines.append("Thank you for shopping with us!")
    message = "\n".join(lines)

    phone = "".join(ch for ch in txn.customer_phone if ch.isdigit())
    import urllib.parse
    link = f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"
    return {"link": link}


# ============================================================
# EMPLOYEE PROFILE (self-service + admin drill-down)
# ============================================================
@app.get("/api/employees/{user_id}/profile", response_model=schemas.EmployeeProfileOut)
def employee_profile(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_self_or_admin(user_id, current_user)
    employee = db.query(User).filter(User.id == user_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)

    today_txns = db.query(Transaction).filter(Transaction.employee_id == user_id, Transaction.created_at >= today_start).all()
    month_txns = db.query(Transaction).filter(Transaction.employee_id == user_id, Transaction.created_at >= month_start).all()

    return schemas.EmployeeProfileOut(
        id=employee.id, name=employee.name, username=employee.username, is_active=employee.is_active,
        today_sales=sum(t.total_amount for t in today_txns),
        today_commission=sum(t.total_commission for t in today_txns),
        today_bills=len(today_txns),
        month_sales=sum(t.total_amount for t in month_txns),
        month_commission=sum(t.total_commission for t in month_txns),
        month_bills=len(month_txns),
    )


@app.get("/api/employees/{user_id}/sales-history", response_model=list[schemas.DailySalesEntry])
def employee_sales_history(
    user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
    start_date: str = None, end_date: str = None,
):
    require_self_or_admin(user_id, current_user)
    query = db.query(Transaction).filter(Transaction.employee_id == user_id)
    if start_date:
        query = query.filter(Transaction.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(Transaction.created_at < datetime.fromisoformat(end_date) + timedelta(days=1))
    else:
        query = query.filter(Transaction.created_at >= datetime.utcnow() - timedelta(days=30))

    txns = query.order_by(Transaction.created_at.desc()).all()
    by_day = {}
    for t in txns:
        day = t.created_at.date().isoformat()
        if day not in by_day:
            by_day[day] = {"sales": 0.0, "commission": 0.0, "bills": 0}
        by_day[day]["sales"] += t.total_amount
        by_day[day]["commission"] += t.total_commission
        by_day[day]["bills"] += 1

    return [
        schemas.DailySalesEntry(date=day, sales=v["sales"], commission=v["commission"], bills=v["bills"])
        for day, v in sorted(by_day.items(), reverse=True)
    ]


@app.get("/api/employees/{user_id}/transactions", response_model=list[schemas.TransactionOut])
def employee_transactions_on_date(
    user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
    date: str = None,
):
    require_self_or_admin(user_id, current_user)
    query = db.query(Transaction).filter(Transaction.employee_id == user_id)
    if date:
        day_start = datetime.fromisoformat(date)
        query = query.filter(Transaction.created_at >= day_start, Transaction.created_at < day_start + timedelta(days=1))
    return query.order_by(Transaction.created_at.desc()).all()


# ============================================================
# ADMIN -- SEARCHABLE TRANSACTION LOG (all bills, filterable)
# ============================================================
@app.get("/api/reports/transactions", response_model=list[schemas.TransactionOut])
def search_transactions(
    db: Session = Depends(get_db), _admin=Depends(require_admin),
    start_date: str = None, end_date: str = None,
    employee_id: int = None, customer_search: str = None,
    limit: int = 200,
):
    query = db.query(Transaction)
    if start_date:
        query = query.filter(Transaction.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(Transaction.created_at < datetime.fromisoformat(end_date) + timedelta(days=1))
    if employee_id:
        query = query.filter(Transaction.employee_id == employee_id)
    if customer_search:
        like = f"%{customer_search}%"
        query = query.filter((Transaction.customer_name.ilike(like)) | (Transaction.customer_phone.ilike(like)))
    return query.order_by(Transaction.created_at.desc()).limit(limit).all()


# ============================================================
# REPORTS (admin only)
# ============================================================
@app.get("/api/reports/daily-summary")
def daily_summary(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    txns = db.query(Transaction).filter(Transaction.created_at >= today_start).all()
    total_sales = sum(t.total_amount for t in txns)
    total_commission = sum(t.total_commission for t in txns)
    by_payment = {}
    for t in txns:
        by_payment[t.payment_method] = by_payment.get(t.payment_method, 0) + t.total_amount
    return {
        "date": today_start.date().isoformat(),
        "total_sales": total_sales,
        "total_transactions": len(txns),
        "total_commission": total_commission,
        "by_payment_method": by_payment,
    }


@app.get("/api/reports/employee-sales")
def employee_sales(db: Session = Depends(get_db), _admin=Depends(require_admin), days: int = 1):
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(
            User.id, User.name,
            func.coalesce(func.sum(Transaction.total_amount), 0.0).label("total_sales"),
            func.coalesce(func.sum(Transaction.total_commission), 0.0).label("total_commission"),
            func.count(Transaction.id).label("num_transactions"),
        )
        .join(Transaction, Transaction.employee_id == User.id)
        .filter(Transaction.created_at >= since)
        .group_by(User.id)
        .order_by(func.sum(Transaction.total_amount).desc())
        .all()
    )
    return [
        {
            "employee_id": r.id, "name": r.name, "total_sales": r.total_sales,
            "total_commission": r.total_commission, "num_transactions": r.num_transactions,
        }
        for r in rows
    ]


@app.get("/api/reports/product-sales")
def product_sales(db: Session = Depends(get_db), _admin=Depends(require_admin), days: int = 1):
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(
            Product.id, Product.name,
            func.coalesce(func.sum(TransactionItem.quantity), 0).label("units_sold"),
            func.coalesce(func.sum(TransactionItem.price_at_sale * TransactionItem.quantity), 0.0).label("revenue"),
        )
        .join(TransactionItem, TransactionItem.product_id == Product.id)
        .join(Transaction, Transaction.id == TransactionItem.transaction_id)
        .filter(Transaction.created_at >= since)
        .group_by(Product.id)
        .order_by(func.sum(TransactionItem.quantity).desc())
        .all()
    )
    return [{"product_id": r.id, "name": r.name, "units_sold": r.units_sold, "revenue": r.revenue} for r in rows]


@app.get("/api/reports/low-stock")
def low_stock(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    products = db.query(Product).filter(Product.quantity <= Product.low_stock_threshold).order_by(Product.quantity).all()
    return [
        {"id": p.id, "name": p.name, "quantity": p.quantity, "threshold": p.low_stock_threshold}
        for p in products
    ]


@app.get("/api/reports/stock-logs")
def stock_logs(db: Session = Depends(get_db), _admin=Depends(require_admin), product_id: int = None, limit: int = 100):
    query = db.query(StockLog).order_by(StockLog.created_at.desc())
    if product_id:
        query = query.filter(StockLog.product_id == product_id)
    logs = query.limit(limit).all()
    result = []
    for log in logs:
        product = db.query(Product).filter(Product.id == log.product_id).first()
        result.append({
            "id": log.id,
            "product_name": product.name if product else "Deleted product",
            "change": log.change,
            "reason": log.reason,
            "note": log.note,
            "created_at": log.created_at.isoformat(),
        })
    return result


# ============================================================
# STATIC FRONTEND
# ============================================================
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")


@app.get("/")
def serve_login():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/admin")
def serve_admin():
    return FileResponse(os.path.join(FRONTEND_DIR, "admin.html"))


@app.get("/billing")
def serve_billing():
    return FileResponse(os.path.join(FRONTEND_DIR, "billing.html"))


@app.get("/my-sales")
def serve_my_sales():
    return FileResponse(os.path.join(FRONTEND_DIR, "my-sales.html"))
