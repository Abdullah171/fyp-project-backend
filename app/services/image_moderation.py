# app/services/image_moderation.py
from __future__ import annotations

from io import BytesIO
from typing import Tuple, Optional

from PIL import Image, ImageFilter
from nudenet import NudeDetector

import torch
from torch.nn import functional as F
from transformers import AutoModelForImageClassification, ViTImageProcessor


# ---------- GLOBAL SINGLETONS ----------

_detector: NudeDetector | None = None
_clf_model: Optional[AutoModelForImageClassification] = None
_clf_processor: Optional[ViTImageProcessor] = None

# If you have a GPU and want to use it, change this to "cuda"
_DEVICE = "cpu"


# ---------- LOADING HELPERS ----------

def get_detector() -> NudeDetector:
    """
    Lazy-load NudeNet detector (bounding boxes for explicit body parts).
    """
    global _detector
    if _detector is None:
        _detector = NudeDetector()
    return _detector


def get_classifier() -> tuple[AutoModelForImageClassification, ViTImageProcessor]:
    """
    Lazy-load Falconsai/nsfw_image_detection classifier (whole image NSFW/normal).
    """
    global _clf_model, _clf_processor
    if _clf_model is None:
        _clf_model = AutoModelForImageClassification.from_pretrained(
            "Falconsai/nsfw_image_detection"
        ).to(_DEVICE)
        _clf_model.eval()
        _clf_processor = ViTImageProcessor.from_pretrained(
            "Falconsai/nsfw_image_detection"
        )
    return _clf_model, _clf_processor


# ---------- NUDE DETECTION (NudeNet) ----------

_EXPLICIT_PART_KEYWORDS = (
    "BREAST",
    "GENITALIA",
    "BUTTOCKS",
    "ANUS",
    "VAGINA",
    "PENIS",
)


def _is_explicit_label(label: str) -> bool:
    """
    Check if a NudeNet label/class should be considered explicit.
    Works with labels like:
      - FEMALE_BREAST_EXPOSED
      - MALE_GENITALIA_EXPOSED
      - BUTTOCKS_EXPOSED
      - ANUS_EXPOSED
    """
    lab = label.upper()
    if "EXPOSED" not in lab:
        return False
    return any(part in lab for part in _EXPLICIT_PART_KEYWORDS)


def is_nude_by_detector(image_bytes: bytes, threshold: float) -> bool:
    """
    Use NudeNet detector to see if there are explicit exposed parts
    with confidence >= threshold.
    """
    det = get_detector()
    detections = det.detect(image_bytes)

    # Uncomment for debugging:
    # print("NudeNet detections:", detections)

    for r in detections:
        label = (r.get("label") or r.get("class") or "").upper()
        score = float(r.get("score", 0.0))

        if _is_explicit_label(label) and score >= threshold:
            return True

    return False


# ---------- NSFW CLASSIFIER (Falconsai/nsfw_image_detection) ----------

def nsfw_score_classifier(image_bytes: bytes) -> float:
    """
    Returns probability that image is NSFW according to Falconsai/nsfw_image_detection.
    """
    model, processor = get_classifier()
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    inputs = processor(images=img, return_tensors="pt").to(_DEVICE)

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits  # shape [1, 2] -> [normal, nsfw] or similar

    probs = F.softmax(logits, dim=-1)[0]
    # Find which index corresponds to "nsfw"
    # model.config.id2label might be e.g. {0: 'DRAWINGS', 1: 'HENTAI', ...}
    id2label = model.config.id2label
    nsfw_idx = None
    for idx, lab in id2label.items():
        if lab.lower().startswith("nsfw") or lab.lower() == "nsfw":
            nsfw_idx = int(idx)
            break

    if nsfw_idx is None:
        # Fallback: assume class with label containing "nsfw" or just last index
        # but ideally this branch never hits.
        nsfw_idx = int(probs.argmax().item())

    return float(probs[nsfw_idx].item())


def _classifier_threshold_for_detector_threshold(detector_threshold: float) -> float:
    """
    Map the NudeNet threshold to a reasonable NSFW probability threshold.

    - Moderate mode calls censor_if_needed with threshold ~0.8
      -> require high classifier confidence to blur (e.g. 0.9)

    - Strict mode calls censor_if_needed with threshold ~0.6
      -> accept lower classifier confidence (e.g. 0.75)
    """
    if detector_threshold >= 0.75:
        # moderate / very strict detector -> use high NSFW prob
        return 0.90
    else:
        # strict detector -> allow more aggressive classification-based blur
        return 0.75


# ---------- BLUR + MAIN ENTRYPOINT ----------

def blur_image(image_bytes: bytes, radius: int = 25) -> bytes:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    blurred = image.filter(ImageFilter.GaussianBlur(radius=radius))
    out = BytesIO()
    blurred.save(out, format="JPEG", quality=85)
    return out.getvalue()


def censor_if_needed(
    image_bytes: bytes,
    threshold: float = 0.5,
    use_classifier: bool = True,
) -> Tuple[bytes, bool]:
    """
    Hybrid censorship:
      1) NudeNet detector for explicit exposed parts
      2) NSFW classifier for overall sexual/NSFW context (e.g. couple intimacy)

    'threshold' is the detector (NudeNet) confidence threshold.
    Classifier threshold is derived from it (more strict for "moderate" mode,
    more aggressive for "strict" mode).
    """
    nude = False

    # 1) Try NudeNet detector
    try:
        if is_nude_by_detector(image_bytes, threshold=threshold):
            nude = True
    except Exception:
        # If NudeNet fails, we fall back to classifier only (if enabled)
        nude = False

    # 2) Classifier fallback / complement
    if not nude and use_classifier:
        try:
            nsfw_prob = nsfw_score_classifier(image_bytes)
            clf_thresh = _classifier_threshold_for_detector_threshold(threshold)

            # Uncomment to debug:
            # print(f"NSFW prob={nsfw_prob:.3f}, threshold={clf_thresh:.3f}")

            if nsfw_prob >= clf_thresh:
                nude = True
        except Exception:
            # Don't break search on ML failure
            nude = False

    if nude:
        return blur_image(image_bytes), True

    return image_bytes, False
