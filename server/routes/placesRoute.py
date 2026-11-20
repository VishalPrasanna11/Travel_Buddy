"""
Google Places photo proxy and place details.

GET /api/places/photo/{ref}?w=640
    Fetches the photo server-side so the API key never reaches the browser.
    Returns image bytes with X-Photo-Width / X-Photo-Height and (when known)
    X-Photo-Attribution headers. Cached in memory (LRU).
GET /api/places/{place_id}
    Enriched place details (hours, reviews, editorial summary).
"""
import asyncio
import json
import logging
import re
import struct
import time
from collections import OrderedDict
from typing import Optional, Tuple
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Path, Query, Response

from tools.google_places_common import attributions_for, google_api_key, place_details

router = APIRouter()
logger = logging.getLogger("places_route")

PHOTO_REF = re.compile(r"^places/[A-Za-z0-9_-]{1,300}/photos/[A-Za-z0-9_-]{1,1200}$")
PLACE_ID = re.compile(r"^[A-Za-z0-9_-]{1,300}$")
ALLOWED_WIDTHS = (160, 240, 320, 400, 480, 640, 800, 960, 1200, 1600)
CACHE_MAX_BYTES = 48 * 1024 * 1024
CACHE_TTL_S = 24 * 3600


class _PhotoCache:
    def __init__(self):
        self.items: "OrderedDict[str, Tuple[float, bytes, str, Optional[Tuple[int, int]]]]" = OrderedDict()
        self.size = 0

    def get(self, key):
        item = self.items.get(key)
        if not item:
            return None
        if time.time() - item[0] > CACHE_TTL_S:
            self.pop(key)
            return None
        self.items.move_to_end(key)
        return item

    def pop(self, key):
        item = self.items.pop(key, None)
        if item:
            self.size -= len(item[1])

    def put(self, key, body: bytes, ctype: str, dims):
        self.pop(key)
        self.items[key] = (time.time(), body, ctype, dims)
        self.size += len(body)
        while self.size > CACHE_MAX_BYTES and self.items:
            old, _ = next(iter(self.items.items()))
            self.pop(old)


_cache = _PhotoCache()
_inflight: dict = {}


def image_size(data: bytes) -> Optional[Tuple[int, int]]:
    """Width/height from JPEG, PNG or WebP headers (no imaging dependency)."""
    try:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", data[16:24])
            return w, h
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            chunk = data[12:16]
            if chunk == b"VP8X":
                w = 1 + int.from_bytes(data[24:27], "little")
                h = 1 + int.from_bytes(data[27:30], "little")
                return w, h
            if chunk == b"VP8 ":
                w, h = struct.unpack("<HH", data[26:30])
                return w & 0x3FFF, h & 0x3FFF
            if chunk == b"VP8L":
                b = data[21:25]
                w = 1 + (((b[1] & 0x3F) << 8) | b[0])
                h = 1 + (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
                return w, h
        if data[:2] == b"\xff\xd8":
            i = 2
            while i < len(data) - 9:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w, h
                seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
                i += 2 + seg_len
    except Exception:
        return None
    return None


async def _fetch_photo(ref: str, width: int):
    key = google_api_key()
    if not key:
        raise HTTPException(status_code=503, detail="Photos aren't configured.")
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(
            f"https://places.googleapis.com/v1/{ref}/media",
            params={"maxWidthPx": width, "key": key},
        )
        if resp.status_code == 404 or resp.status_code == 400:
            raise HTTPException(status_code=404, detail="Photo not found.")
        if resp.status_code >= 400:
            raise HTTPException(status_code=502, detail="The photo provider returned an error.")
        ctype = resp.headers.get("content-type", "image/jpeg").split(";")[0]
        if not ctype.startswith("image/"):
            raise HTTPException(status_code=502, detail="The photo provider returned something that isn't an image.")
        body = resp.content
    return body, ctype, image_size(body)


@router.get("/photo/{ref:path}")
async def place_photo(
    ref: str = Path(..., description="Google photo resource name, places/{place}/photos/{photo}"),
    w: int = Query(640, ge=64, le=1600, description="Max width in px (rounded up to a cached size)"),
):
    if not PHOTO_REF.match(ref):
        raise HTTPException(status_code=400, detail="Invalid photo reference.")
    width = next((x for x in ALLOWED_WIDTHS if x >= w), ALLOWED_WIDTHS[-1])
    cache_key = f"{ref}@{width}"
    item = _cache.get(cache_key)
    if not item:
        # Coalesce concurrent requests for the same photo into one upstream fetch.
        fut = _inflight.get(cache_key)
        if fut is None:
            fut = asyncio.ensure_future(_fetch_photo(ref, width))
            _inflight[cache_key] = fut
            fut.add_done_callback(lambda _f: _inflight.pop(cache_key, None))
        body, ctype, dims = await fut
        _cache.put(cache_key, body, ctype, dims)
        item = (time.time(), body, ctype, dims)
    _, body, ctype, dims = item

    headers = {
        "Cache-Control": "public, max-age=86400, immutable",
        "Access-Control-Expose-Headers": "X-Photo-Width, X-Photo-Height, X-Photo-Attribution",
    }
    if dims:
        headers["X-Photo-Width"], headers["X-Photo-Height"] = str(dims[0]), str(dims[1])
    attrs = attributions_for(ref)
    if attrs:
        # Header values must be latin-1; percent-encode the JSON.
        headers["X-Photo-Attribution"] = quote(json.dumps(attrs, separators=(",", ":")), safe="")
    return Response(content=body, media_type=ctype, headers=headers)


@router.get("/{place_id}")
async def get_place(place_id: str = Path(...)):
    if not PLACE_ID.match(place_id):
        raise HTTPException(status_code=400, detail="Invalid place id.")
    key = google_api_key()
    if not key:
        raise HTTPException(status_code=503, detail="Places aren't configured.")
    place = await asyncio.to_thread(place_details, place_id, key)
    if not place:
        raise HTTPException(status_code=404, detail="Place not found.")
    return place.model_dump(mode="json", exclude_none=True)
