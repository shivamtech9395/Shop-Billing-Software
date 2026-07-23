# Dukaan Manager — Inventory + Billing System

A complete inventory + billing system that scans products via QR code,
tracks employee-wise sales, calculates product-level commission, and
shares bills with customers via PDF/WhatsApp.

## What's included

- **Two roles**: Admin (full access) and Employee (billing/scan only)
- **Product management**: Add/edit products, price, stock, low-stock alerts
- **QR label generation**: Every product gets a unique QR — print and stick it on the product
- **Two scan modes**: Mobile/laptop camera, OR a dedicated barcode/QR scanner
  device at the counter (switch anytime from Settings)
- **Scan-then-confirm flow**: Scanning shows a preview card first — you tap
  "Add to Bill" to confirm. This prevents the same item getting added twice
  from an accidental double-scan.
- **Customer details on bill**: Capture customer name + phone at checkout
- **Bill sharing**: View/print/download the bill as a PDF, or share a
  pre-filled summary via WhatsApp (see note below on how this works)
- **Employee self-service ("My Sales")**: Every employee can see their own
  today's sales, commission earned, and search their sales history by date
- **Admin employee profiles**: Click any employee to see their sales,
  commission, and full history — full transparency for the owner
- **Searchable bill log**: Filter all bills by date range, employee, or
  customer name/phone
- **Trending products**: Dashboard shows which products are selling fastest
- **Stock audit trail**: Every stock change (sale/restock/correction) is
  logged with a reason — makes shrinkage/theft easy to catch
- **Reports**: Today/7-day/30-day sales, employee performance, product-wise
  sales, low-stock list

## How WhatsApp sharing actually works (important)

There is no way for any third-party app to auto-send WhatsApp messages or
attachments without WhatsApp's paid Business API. What this app does instead:

1. It builds a `wa.me` link with the bill summary already typed out
2. Tapping "Share on WhatsApp" opens WhatsApp (app or web) with that message ready
3. You just tap **Send** — and if you want to send the actual PDF, download
   it first and attach it manually in the chat

This is the same approach every small-business billing app uses without a
paid WhatsApp Business subscription.

## How to run it

### Requirements
- Python 3.10 or newer (`python3 --version` to check)

### Steps

```bash
cd inventory-system/backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then open: **http://localhost:8000**

Or on Windows, just double-click `backend/start_server.bat` — it runs on
port 8090 automatically (`http://localhost:8090`) to avoid clashing with
anything already using port 8000.

**Default admin login** (first time only):
- Username: `admin`
- Password: `admin123`

⚠️ Change this password after logging in for the first time — for now,
create a new admin from the Employees tab and deactivate the default one.
A password-change screen is on the roadmap.

## Using it from other devices (phones, counter tablets, etc.)

This is a web app, so any device's browser works — no separate app to install:

1. On the computer running the server, find its local IP address
   (Windows: `ipconfig`, Mac/Linux: `ifconfig` or `ip addr` — something like `192.168.1.5`)
2. Connect the phone/tablet to the **same WiFi**
3. Open `http://192.168.1.5:8000` (use your actual IP) in that device's browser
4. Employees log in with their own username/password and can scan with
   their own camera immediately

For access from outside the shop (over the internet), you'd need to deploy
this to a cloud server (Railway, Render, a VPS, etc.) — see "Next Phases" below.

## Employee workflow

1. Employee logs in → lands on the **Billing** screen
2. Scans a product (camera or scanner) → a preview card appears
3. Adjusts quantity if needed, taps **"Add to Bill"** to confirm
4. Repeats for more items, then taps **"Create Bill"**
5. Optionally enters customer name/phone
6. Bill is created → options to print/download PDF or share on WhatsApp
7. Anytime, the employee can open **"My Sales"** (bottom nav) to see their
   own commission and sales history — full transparency, nothing hidden

## Admin workflow

- **Dashboard**: today's totals, low-stock alerts, employee performance, trending products
- **Products**: add/edit products, generate + print QR labels, adjust stock with a reason
- **Employees**: create logins, click "View Profile" on any employee to see
  their sales/commission and search their history by date
- **Bills**: search every bill by date range, employee, or customer — click
  any row to see the full itemized bill and print it
- **Reports**: switch between Today / Last 7 days / Last 30 days for
  employee and product performance, plus the full stock activity log

## Project structure

```
inventory-system/
  backend/
    main.py           -> all API routes
    database.py        -> database models (SQLite)
    auth.py              -> login/JWT
    schemas.py            -> request/response validation
    qr_utils.py             -> QR code generation
    pdf_utils.py              -> PDF receipt generation
    requirements.txt
    start_server.bat            -> Windows one-click start (port 8090)
  frontend/
    index.html          -> login page
    admin.html            -> admin dashboard
    billing.html            -> employee scan+bill screen
    my-sales.html              -> employee self-service sales history
    static/css, static/js
```

The database is a single file (`backend/inventory.db`) created automatically
on first run. To back it up, just copy that file.

## Next Phases (roadmap)

- **Phase 3**: Password-change UI, product images, barcode (not just QR) support
- **Phase 4**: Multi-shop / multi-branch support
- **Phase 5**: Cloud deployment guide, subscription/SaaS billing if you want
  to sell this to other shops

## Important security note

`backend/auth.py` has a placeholder `SECRET_KEY`. Before deploying this
anywhere real shops will use it (especially over the internet), change it
to a random 32+ character string.
