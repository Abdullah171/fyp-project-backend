# app/routers/media.py
from io import BytesIO
from urllib.parse import unquote_plus

import requests
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse

from ..services.image_moderation import censor_if_needed
from ..utils.settings import get_or_create_global_settings
from ..models import FilterMode
from sqlalchemy.orm import Session
from ..database import get_db

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/proxy")
def proxy_image(
    url: str = Query(..., description="Original image URL (URL-encoded)"),
    mode: FilterMode | None = Query(
        None,
        description="Optional override for filter mode: relaxed/moderate/strict",
    ),
    db: Session = Depends(get_db),
):
    """
    Downloads an image from the given URL, applies censorship depending
    on filter_mode (relaxed / moderate / strict), and returns the (possibly blurred) image.

    Frontend should always use this endpoint for thumbnails:
        <img src={`/api/media/proxy?url=${encodeURIComponent(img_src)}&mode=${filterMode}`} />
    """
    decoded_url = unquote_plus(url)

    if not decoded_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid image URL")

    try:
        resp = requests.get(decoded_url, timeout=10)
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Failed to fetch remote image")

    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Image not found")

    content_type = resp.headers.get("content-type", "")
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="URL does not point to an image")

    original_bytes = resp.content

    settings = get_or_create_global_settings(db)
    effective_mode = mode or settings.filter_mode

    # Relaxed: no censorship at all
    if effective_mode == FilterMode.relaxed:
        censored_bytes = original_bytes

    # Moderate: only very obvious nudity/NSFW gets blurred
    elif effective_mode == FilterMode.moderate:
        censored_bytes, _ = censor_if_needed(original_bytes, threshold=0.8)

    # Strict: more aggressive – catches explicit + many intimate NSFW images
    else:  # strict
        censored_bytes, _ = censor_if_needed(original_bytes, threshold=0.6)

    return StreamingResponse(BytesIO(censored_bytes), media_type="image/jpeg")
