"""
POST /api/book/{entity_id}

Turns a flight / hotel / car result into a RouteStack checkout link on
demand (only when the traveler clicks "Book"), using the raw offer kept
server-side in tools.offer_cache. Returns {"url": …} for deeplink checkout.
When the account is configured for in-app (ACP/Stripe) checkout only, there
is no link to open and we say so instead of inventing one.
"""
import asyncio
import logging
from typing import Any, Dict, Iterable, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path

from middlewares.auth import Identity, require_identity
from tools import offer_cache
from tools.routestack_auth import BASE_URL, headers

router = APIRouter()
logger = logging.getLogger("booking")


def _post(path: str, body: Dict[str, Any], timeout: float = 45) -> Dict[str, Any]:
    resp = httpx.post(f"{BASE_URL}{path}", headers=headers(), json=body, timeout=timeout)
    if resp.status_code >= 400:
        logger.warning(f"{path} -> {resp.status_code}: {resp.text[:300]}")
        raise HTTPException(status_code=502, detail="The booking provider couldn't prepare checkout. Try searching again.")
    return resp.json()


def _walk(obj: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _checkout_url(resp: Dict[str, Any]) -> Optional[str]:
    for d in _walk(resp):
        for key in ("url", "paymentUrl", "deeplink", "redirectUrl"):
            v = d.get(key)
            if isinstance(v, str) and v.startswith("http"):
                return v
    return None


def _cheapest_rate(resp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """First/cheapest object carrying both recommendationId and roomId."""
    best = None
    for d in _walk(resp):
        if d.get("recommendationId") and (d.get("roomId") or d.get("id")):
            price = d.get("ourprice") or d.get("price") or d.get("totalPrice")
            try:
                price = float(price) if price is not None else float("inf")
            except (TypeError, ValueError):
                price = float("inf")
            if best is None or price < best[0]:
                best = (price, d)
    return best[1] if best else None


def _book_flight(offer: Dict[str, Any], ident: Identity) -> Dict[str, Any]:
    body = {k: v for k, v in offer.items() if k != "kind" and v is not None}
    body["routestack_external_userid"] = ident.sub
    return _post("/mcp/flight/get-payment-url", body)


def _book_hotel(offer: Dict[str, Any], ident: Identity) -> Dict[str, Any]:
    base = {k: offer[k] for k in ("hotelId", "hotelName", "token", "correlationId", "checkIn", "checkOut", "rooms", "roomCount", "destinationId") if offer.get(k) is not None}
    rates = _post("/mcp/hotel/get-hotel-details-and-rates", {**base, "contentType": "ALL"})
    rate = _cheapest_rate(rates)
    if not rate:
        raise HTTPException(status_code=409, detail="No bookable room is available for those dates any more.")
    token = next((d.get("token") for d in _walk(rates) if isinstance(d.get("token"), str)), None) or offer.get("token")
    pick = {**base, "token": token, "recommendationId": rate["recommendationId"], "roomId": rate.get("roomId") or rate.get("id")}
    if offer.get("publishedRate") is not None:
        pick["publishedRate"] = offer["publishedRate"]
    check = _post("/mcp/hotel/revalidate", pick)
    return _post("/mcp/hotel/get-payment-url", {
        **pick,
        "priceCheckResult": check.get("result") if isinstance(check.get("result"), dict) else check,
        "travellers": [{"numOfAdults": r.get("adults", 1), "childAges": r.get("childAges", [])} for r in offer.get("rooms") or []],
        "routestack_external_userid": ident.sub,
    })


def _book_car(offer: Dict[str, Any], ident: Identity) -> Dict[str, Any]:
    body = {k: v for k, v in offer.items() if k != "kind" and v is not None}
    body["routestack_external_userid"] = ident.sub
    return _post("/mcp/car/get-payment-url", body)


@router.post("/{entity_id}")
async def book(entity_id: str = Path(..., max_length=64), ident: Identity = Depends(require_identity)):
    offer = offer_cache.get(entity_id)
    if not offer:
        raise HTTPException(status_code=410, detail="This price has expired. Ask again to get fresh results.")
    handler = {"flight": _book_flight, "hotel": _book_hotel, "car": _book_car}.get(offer["kind"])
    if not handler:
        raise HTTPException(status_code=400, detail="This result can't be booked.")
    try:
        resp = await asyncio.to_thread(handler, offer, ident)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("booking failed")
        raise HTTPException(status_code=502, detail=f"Booking link failed: {str(e)[:160]}")
    url = _checkout_url(resp)
    mode = resp.get("checkoutMode") or ("deeplink" if url else None)
    if url:
        return {"url": url, "checkout_mode": mode, "kind": offer["kind"]}
    raise HTTPException(
        status_code=409,
        detail="This provider only supports in-app checkout, which TravelBuddy doesn't offer yet.",
    )
