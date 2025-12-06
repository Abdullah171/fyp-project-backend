# app/services/image_moderation.py
from __future__ import annotations

from io import BytesIO
from typing import Tuple

from PIL import Image, ImageFilter
from nudenet import NudeDetector


_detector: NudeDetector | None = None


def get_detector() -> NudeDetector:
    global _detector
    if _detector is None:
        _detector = NudeDetector()
    return _detector


def _is_explicit_label(raw_label: str) -> bool:
    """
    Handle both NudeNet 2.x style labels (EXPOSED_BREAST_F) and 3.x style
    (FEMALE_BREAST_EXPOSED, MALE_GENITALIA_EXPOSED, etc.).
    """
    label = raw_label.upper()

    # Quick reject: must be exposed, not covered
    if "EXPOSED" not in label:
        return False

    # Only treat these regions as explicit
    explicit_parts = ("BREAST", "GENITALIA", "BUTTOCKS", "ANUS")

    return any(part in label for part in explicit_parts)


def is_nude(image_bytes: bytes, threshold: float = 0.5) -> bool:
    det = get_detector()

    # Works with both bytes and paths in NudeNet
    results = det.detect(image_bytes)

    # Debug if you need it:
    print("NudeNet detections:", results)

    for r in results:
        # Newer versions use "class", older use "label"
        label = r.get("label") or r.get("class") or ""
        score = float(r.get("score", 0.0))

        if score >= threshold and _is_explicit_label(label):
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
    except Exception as e:
        # Optional: log e here
        # print("NudeNet failed:", e)
        return image_bytes, False

    if nude:
        return blur_image(image_bytes), True
    return image_bytes, False
