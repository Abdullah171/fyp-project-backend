# app/services/image_moderation.py
from __future__ import annotations

from io import BytesIO
from tempfile import NamedTemporaryFile
from typing import Tuple

from PIL import Image, ImageFilter
from nudenet import NudeDetector


_detector: NudeDetector | None = None

def get_detector() -> NudeDetector:
    global _detector
    if _detector is None:
        _detector = NudeDetector()
    return _detector

def is_nude(image_bytes: bytes, threshold: float = 0.6) -> bool:
    det = get_detector()
    # NudeDetector.detect returns list of detections; you can interpret any detection 
    # with score above threshold as "nude".
    results = det.detect(image_bytes)
    return any(r.get("score", 0.0) >= threshold for r in results)

def blur_image(image_bytes: bytes, radius: int = 25) -> bytes:
    """
    Apply a strong Gaussian blur on the whole image.
    """
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    blurred = image.filter(ImageFilter.GaussianBlur(radius=radius))
    out = BytesIO()
    blurred.save(out, format="JPEG", quality=85)
    return out.getvalue()


def censor_if_needed(image_bytes: bytes) -> Tuple[bytes, bool]:
    """
    Returns (output_image_bytes, was_censored).
    If NudeNet says the image is nude, blur it. Otherwise keep original.
    """
    try:
        nude = is_nude(image_bytes)
    except Exception:
        # If NudeNet fails for some reason, fail open (do not break search)
        return image_bytes, False

    if nude:
        return blur_image(image_bytes), True
    return image_bytes, False
