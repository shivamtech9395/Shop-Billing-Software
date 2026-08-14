"""
Reads a photo of a product's existing manufacturer label/price tag and
extracts the product name and price automatically.

Uses OCR.space -- a genuinely free OCR service (no credit card, 25,000
free requests/month) -- to read the text off the label, then uses simple
pattern matching to guess which part is the price and which part is the
product name.

Requires an OCR_SPACE_API_KEY environment variable (free to get at
https://ocr.space/ocrapi/freekey -- just an email, no card). If it's not
set, the feature is simply unavailable -- everything else in the app
keeps working normally.
"""
import os
import re
import requests

OCR_SPACE_API_KEY = os.environ.get("OCR_SPACE_API_KEY")
OCR_SPACE_URL = "https://api.ocr.space/parse/image"


def is_available() -> bool:
    return bool(OCR_SPACE_API_KEY)


def _parse_label_text(text: str) -> dict:
    """Heuristic parsing: pull a price and a product name out of raw OCR text."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    price = None
    price_patterns = [
        r'(?:MRP|Price|Rs\.?|INR)\s*[:.]?\s*([\d,]+\.?\d*)',
        r'₹\s*([\d,]+\.?\d*)',
    ]
    for pattern in price_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                price = float(match.group(1).replace(",", ""))
                break
            except ValueError:
                pass
    if price is None:
        # fall back to any plain decimal number like "150.00"
        numbers = re.findall(r'\b(\d{1,6}\.\d{2})\b', text)
        if numbers:
            price = float(numbers[0])
    if price is None:
        # last resort: any standalone 2-5 digit number
        numbers = re.findall(r'\b(\d{2,5})\b', text)
        if numbers:
            price = float(numbers[0])

    name = None
    candidate_lines = [
        l for l in lines
        if len(l) > 3
        and not re.match(r'^[\d\s.,₹:/\-]+$', l)
        and not re.match(r'^(MRP|Price|Rs\.?|INR|Batch|Mfg|Exp|Qty|Net\s*Wt)', l, re.IGNORECASE)
    ]
    if candidate_lines:
        name = max(candidate_lines, key=len)[:80]

    return {"name": name, "price": price, "category": None}


def extract_label_info(image_bytes: bytes, media_type: str) -> dict:
    """
    Sends the label photo to OCR.space and extracts product info from the
    text it reads. Returns {"name": str|None, "price": float|None, "category": None}.
    Raises RuntimeError with a human-readable message on failure.
    """
    if not is_available():
        raise RuntimeError(
            "Label scanning isn't set up yet -- a free OCR_SPACE_API_KEY needs to be "
            "added to the server's environment variables first (get one free at "
            "ocr.space/ocrapi/freekey)."
        )

    ext = "jpg" if "jpeg" in media_type or "jpg" in media_type else "png"
    try:
        response = requests.post(
            OCR_SPACE_URL,
            files={"file": (f"label.{ext}", image_bytes, media_type)},
            data={
                "apikey": OCR_SPACE_API_KEY,
                "OCREngine": 2,
                "scale": "true",
                "detectOrientation": "true",
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Could not reach the label-reading service: {e}")
    except ValueError:
        raise RuntimeError("The label-reading service returned an unexpected response.")

    if result.get("IsErroredOnProcessing"):
        error_msg = result.get("ErrorMessage") or "Could not read this image."
        if isinstance(error_msg, list):
            error_msg = " ".join(error_msg)
        raise RuntimeError(f"Couldn't read the label: {error_msg}")

    parsed_results = result.get("ParsedResults") or []
    if not parsed_results:
        raise RuntimeError("Couldn't read any text on this label -- try a clearer, well-lit photo.")

    raw_text = parsed_results[0].get("ParsedText", "").strip()
    if not raw_text:
        raise RuntimeError("Couldn't read any text on this label -- try a clearer, well-lit photo.")

    return _parse_label_text(raw_text)
