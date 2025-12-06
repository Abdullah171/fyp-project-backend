# app/routers/media.py
from io import BytesIO
from urllib.parse import unquote_plus

import requests
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..services.image_moderation import censor_if_needed

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/proxy")
def proxy_image(url: str = Query(..., description="Original image URL (URL-encoded)")):
    """
    Downloads an image from the given URL, runs NudeNet censorship,
    and returns the (possibly blurred) image bytes.

    Frontend should NEVER call remote thumbnails directly. It should always use:
        <img src={`/api/media/proxy?url=${encodeURIComponent(img_src)}`} />
    """
    # Decode in case frontend encoded it
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

    censored_bytes, _ = censor_if_needed(original_bytes)

    # We always send back JPEG; frontend doesn't care about format for thumbnails.
    return StreamingResponse(BytesIO(censored_bytes), media_type="image/jpeg")
