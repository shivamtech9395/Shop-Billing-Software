"""
Generates a simple, printable PDF receipt for a completed transaction.
"""
from fpdf import FPDF


def generate_receipt_pdf(shop_name: str, transaction, employee_name: str) -> bytes:
    pdf = FPDF(format="A5")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=12)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, shop_name, ln=True, align="C")

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Bill #{transaction.id}", ln=True, align="C")
    pdf.cell(0, 6, transaction.created_at.strftime("%d %b %Y, %I:%M %p"), ln=True, align="C")
    pdf.ln(3)

    pdf.set_draw_color(180, 180, 180)
    pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 9)
    if transaction.customer_name:
        pdf.cell(0, 6, f"Customer: {transaction.customer_name}", ln=True)
    if transaction.customer_phone:
        pdf.cell(0, 6, f"Phone: {transaction.customer_phone}", ln=True)
    pdf.cell(0, 6, f"Served by: {employee_name}", ln=True)
    pdf.cell(0, 6, f"Payment: {transaction.payment_method.upper()}", ln=True)
    pdf.ln(4)

    # Table header
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(80, 7, "Item", border="B")
    pdf.cell(20, 7, "Qty", border="B", align="C")
    pdf.cell(30, 7, "Price", border="B", align="R")
    pdf.cell(30, 7, "Total", border="B", align="R", ln=True)

    pdf.set_font("Helvetica", "", 9)
    for item in transaction.items:
        line_total = item.price_at_sale * item.quantity
        pdf.cell(80, 7, item.product_name_snapshot[:38])
        pdf.cell(20, 7, str(item.quantity), align="C")
        pdf.cell(30, 7, f"Rs.{item.price_at_sale:.2f}", align="R")
        pdf.cell(30, 7, f"Rs.{line_total:.2f}", align="R", ln=True)

    pdf.ln(3)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(10, pdf.get_y(), pdf.w - 10, pdf.get_y())
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Total: Rs.{transaction.total_amount:.2f}", ln=True, align="R")

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(140, 140, 140)
    pdf.ln(6)
    pdf.cell(0, 5, "Thank you for shopping with us!", ln=True, align="C")

    return bytes(pdf.output())
