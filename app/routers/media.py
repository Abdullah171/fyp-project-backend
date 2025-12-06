# app/routers/media.py
from io import BytesIO
from urllib.parse import unquote_plus

import requests
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse

from ..services.image_moderation import censor_if_needed
from ..utils.settings import get_or_create_global_settings
from ..models import FilterMode
router = APIRouter(prefix="/media", tags=["media"])
from sqlalchemy.orm import Session
from ..database import get_db


@router.get("/proxy")
def proxy_image(
    url: str = Query(..., description="Original image URL (URL-encoded)"),
    db: Session = Depends(get_db),
):
    """
    Downloads an image from the given URL, runs NudeNet censorship
    depending on current filter_mode, and returns the (possibly blurred) image.

    Frontend should NEVER call remote thumbnails directly. It should always use:
        <img src={`/api/media/proxy?url=${encodeURIComponent(img_src)}`} />
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

    if settings.filter_mode == FilterMode.relaxed:
        censored_bytes = original_bytes
    elif settings.filter_mode == FilterMode.moderate:
        # less aggressive – only blur when very certain
        censored_bytes, _ = censor_if_needed(original_bytes, threshold=0.8)
    else:  # strict
        # more aggressive – but you can still bump this to 0.6–0.7 if it's too much
        censored_bytes, _ = censor_if_needed(original_bytes, threshold=0.6)

    return StreamingResponse(BytesIO(censored_bytes), media_type="image/jpeg")