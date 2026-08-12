"""
Reads a photo of a product's existing manufacturer label/price tag and
extracts the product name and price automatically, using Claude's vision
capability. This saves the shop owner from typing details by hand for
products that already come with a printed label.

Requires an ANTHROPIC_API_KEY environment variable. If it's not set, the
feature is simply unavailable (the endpoint returns a clear error) --
everything else in the app keeps working normally.
"""
import os
import json
import base64
import re

try:
    import anthropic
except ImportError:
    anthropic = None

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


def is_available() -> bool:
    return anthropic is not None and bool(ANTHROPIC_API_KEY)


def extract_label_info(image_bytes: bytes, media_type: str) -> dict:
    """
    Sends the label photo to Claude and asks for structured product info.
    Returns a dict: {"name": str|None, "price": float|None, "category": str|None}
    Raises RuntimeError with a human-readable message on failure.
    """
    if not is_available():
        raise RuntimeError(
            "Label scanning isn't set up yet -- an ANTHROPIC_API_KEY needs to be "
            "added to the server's environment variables first."
        )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")

    prompt = (
        "This is a photo of a product's price tag or manufacturer label from a "
        "retail shop. Read it and extract the product details. "
        "Respond with ONLY a JSON object, no other text, in exactly this shape: "
        '{"name": "<short product name>", "price": <number or null>, "category": "<short category guess or null>"}. '
        "Keep the name concise (brand + product, not the full marketing description). "
        "If the price isn't clearly visible, use null for price. "
        "If you can't identify a product on this image at all, return "
        '{"name": null, "price": null, "category": null}.'
    )

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64_image}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
    except Exception as e:
        raise RuntimeError(f"Could not reach the label-reading service: {e}")

    raw_text = "".join(block.text for block in message.content if hasattr(block, "text")).strip()

    # Strip markdown code fences if the model wrapped the JSON in them
    raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        raise RuntimeError("Couldn't read the label clearly -- try a clearer, well-lit photo.")

    return {
        "name": data.get("name") or None,
        "price": data.get("price") if isinstance(data.get("price"), (int, float)) else None,
        "category": data.get("category") or None,
    }
