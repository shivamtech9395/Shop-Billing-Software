"""
QR generation. Each product gets a short random unique code (not the price
or name) so that changing the price never invalidates a printed label.
"""
import qrcode
import io
import secrets


def generate_qr_id() -> str:
    # e.g. "PRD-8F2A1C9B" -- unique, short, unambiguous when printed small
    return "PRD-" + secrets.token_hex(4).upper()


def generate_qr_image_bytes(data: str) -> bytes:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
