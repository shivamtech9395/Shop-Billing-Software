"""
Generates a clean, professional-looking printable PDF receipt for a
completed transaction -- shop name/address/phone in a colored header band,
a proper itemized table, and a highlighted total.
"""
from fpdf import FPDF

NAVY = (22, 50, 79)
AMBER = (232, 163, 61)
LIGHT_GRAY = (245, 245, 245)
MID_GRAY = (140, 140, 140)
DARK = (30, 30, 30)


def generate_receipt_pdf(shop_name: str, transaction, employee_name: str, shop_address: str = "", shop_phone: str = "") -> bytes:
    pdf = FPDF(format="A5")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=14)
    page_w = pdf.w
    margin = 12
    content_w = page_w - 2 * margin

    # ---------- Header band ----------
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, page_w, 34, style="F")

    pdf.set_xy(margin, 8)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(content_w, 9, shop_name, ln=True)

    pdf.set_x(margin)
    pdf.set_font("Helvetica", "", 9)
    contact_line = " | ".join(filter(None, [shop_address, shop_phone]))
    if contact_line:
        pdf.cell(content_w, 6, contact_line, ln=True)

    # Bill number + date, right-aligned inside the band
    pdf.set_xy(margin, 8)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(content_w, 6, f"Bill #{transaction.id}", align="R", ln=True)
    pdf.set_x(margin)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(content_w, 6, transaction.created_at.strftime("%d %b %Y, %I:%M %p"), align="R")

    pdf.set_y(40)
    pdf.set_text_color(*DARK)

    # ---------- Customer / staff / payment info ----------
    pdf.set_font("Helvetica", "", 9.5)
    left_x = margin
    if transaction.customer_name or transaction.customer_phone:
        label = transaction.customer_name or "Walk-in customer"
        if transaction.customer_phone:
            label += f"  ·  {transaction.customer_phone}"
        pdf.set_x(left_x)
        pdf.cell(content_w, 6, f"Customer: {label}", ln=True)

    pdf.set_x(left_x)
    pdf.set_text_color(*MID_GRAY)
    pdf.cell(content_w / 2, 6, f"Served by {employee_name}")
    pdf.cell(content_w / 2, 6, f"Payment: {transaction.payment_method.upper()}", align="R", ln=True)
    pdf.set_text_color(*DARK)
    pdf.ln(3)

    # ---------- Item table ----------
    col_item, col_qty, col_price, col_total = content_w * 0.44, content_w * 0.14, content_w * 0.21, content_w * 0.21

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*LIGHT_GRAY)
    pdf.set_x(margin)
    pdf.cell(col_item, 8, "  Item", fill=True)
    pdf.cell(col_qty, 8, "Qty", align="C", fill=True)
    pdf.cell(col_price, 8, "Price", align="R", fill=True)
    pdf.cell(col_total, 8, "Total  ", align="R", fill=True, ln=True)

    pdf.set_font("Helvetica", "", 9.5)
    fill = False
    for item in transaction.items:
        line_total = item.price_at_sale * item.quantity
        pdf.set_x(margin)
        if fill:
            pdf.set_fill_color(*LIGHT_GRAY)
        name = item.product_name_snapshot
        if len(name) > 34:
            name = name[:33] + "…"
        pdf.cell(col_item, 8, f"  {name}", fill=fill)
        pdf.cell(col_qty, 8, str(item.quantity), align="C", fill=fill)
        pdf.cell(col_price, 8, f"Rs.{item.price_at_sale:,.2f}", align="R", fill=fill)
        pdf.cell(col_total, 8, f"Rs.{line_total:,.2f}  ", align="R", fill=fill, ln=True)
        fill = not fill

    pdf.ln(2)

    # ---------- Total band ----------
    pdf.set_fill_color(*AMBER)
    pdf.set_x(margin)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*NAVY)
    pdf.cell(content_w, 11, f"  Total:   Rs.{transaction.total_amount:,.2f}  ", align="R", fill=True, ln=True)
    pdf.set_text_color(*DARK)

    # ---------- Footer ----------
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*MID_GRAY)
    pdf.cell(content_w, 5, "Thank you for shopping with us!", align="C", ln=True)
    if shop_phone:
        pdf.set_font("Helvetica", "", 7.5)
        pdf.cell(content_w, 5, f"Questions about this bill? Call {shop_phone}", align="C", ln=True)

    return bytes(pdf.output())