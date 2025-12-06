# app/services/image_moderation.py
from __future__ import annotations
from io import BytesIO
from typing import Tuple, Optional

from PIL import Image, ImageFilter
from nudenet import NudeDetector

# new imports
import torch
from transformers import AutoModelForImageClassification, ViTImageProcessor

_detector: NudeDetector | None = None
_classifier_model: Optional[AutoModelForImageClassification] = None
_classifier_processor: Optional[ViTImageProcessor] = None

def get_detector() -> NudeDetector:
    global _detector
    if _detector is None:
        _detector = NudeDetector()
    return _detector

def get_classifier():
    global _classifier_model, _classifier_processor
    if _classifier_model is None:
        _classifier_model = AutoModelForImageClassification.from_pretrained(
            "Falconsai/nsfw_image_detection"
        )
        _classifier_processor = ViTImageProcessor.from_pretrained(
            "Falconsai/nsfw_image_detection"
        )
    return _classifier_model, _classifier_processor

def classify_nsfw(image_bytes: bytes) -> bool:
    model, proc = get_classifier()
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    inputs = proc(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
    cls_idx = logits.argmax(-1).item()
    label = model.config.id2label[cls_idx]
    return (label.lower() == "nsfw")

def censor_if_needed(image_bytes: bytes, threshold: float = 0.5) -> Tuple[bytes, bool]:
    # first, run detector (your existing logic)
    det = get_detector()
    detections = det.detect(image_bytes)
    # your existing detection logic...
    # For brevity, suppose you have a helper is_nude_by_detector(...)
    if is_nude_by_detector(detections, threshold):
        return blur_image(image_bytes), True

    # then run classifier as fallback
    try:
        if classify_nsfw(image_bytes):
            return blur_image(image_bytes), True
    except Exception:
        # classifier failure — optionally log
        pass

    # otherwise safe
    return image_bytes, False
