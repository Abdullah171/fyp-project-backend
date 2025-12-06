# app/services/image_moderation.py
from __future__ import annotations
from io import BytesIO
from typing import Tuple
from PIL import Image, ImageFilter
from nudenet import NudeDetector

_detector: NudeDetector | None = None

# Body-part categories to treat as “definitely explicit”
EXPLICIT_LABEL_KEYWORDS = {
    "BREAST",       # female or male
    "GENITALIA",
    "BUTTOCKS",
    "ANUS",
    "VAGINA",
    "PENIS"
    # maybe also "VAGINA", "PENIS" if model uses those
}

def get_detector() -> NudeDetector:
    global _detector
    if _detector is None:
        _detector = NudeDetector()
    return _detector

def is_nude(image_bytes: bytes, threshold: float = 0.3) -> bool:
    det = get_detector()
    detections = det.detect(image_bytes)

    for r in detections:
        cls = (r.get("label") or r.get("class") or "").upper()
        score = float(r.get("score", 0.0))

        # Skip obviously non-explicit body parts
        if any(part in cls for part in EXPLICIT_LABEL_KEYWORDS):
            # you can tune per-part threshold:
            # e.g. more suspicious parts like GENITALIA/BUTTOCKS use lower threshold
            if score >= threshold:
                return True
    return False

def blur_image(image_bytes: bytes, radius: int = 25) -> bytes:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    blurred = image.filter(ImageFilter.GaussianBlur(radius=radius))
    out = BytesIO()
    blurred.save(out, format="JPEG", quality=85)
    return out.getvalue()

def censor_if_needed(image_bytes: bytes, threshold: float = 0.5) -> Tuple[bytes, bool]:
    try:
        nude = is_nude(image_bytes, threshold=threshold)
    except Exception:
        return image_bytes, False
    if nude:
        return blur_image(image_bytes), True
    return image_bytes, False
