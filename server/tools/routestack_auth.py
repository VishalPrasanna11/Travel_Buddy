import os
import time
import uuid
import hmac
import hashlib
import base64
import logging
import httpx

logger = logging.getLogger("routestack_auth")

BASE_URL = os.getenv("ROUTESTACK_BASE_URL", "https://mcp.routestack.ai")

_cached_token = None
_token_expiry = 0


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def get_token() -> str:
    global _cached_token, _token_expiry

    if _cached_token and time.time() < _token_expiry - 300:
        return _cached_token

    api_key = os.getenv("ROUTESTACK_API_KEY")
    api_secret = os.getenv("ROUTESTACK_API_SECRET")
    if not api_key or not api_secret:
        raise ValueError("ROUTESTACK_API_KEY and ROUTESTACK_API_SECRET must be set")

    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    message = f"{api_key}:{timestamp}:{nonce}"
    signature = _base64url_encode(
        hmac.new(api_secret.encode(), message.encode(), hashlib.sha256).digest()
    )

    resp = httpx.post(
        f"{BASE_URL}/mcp/auth/partner-token",
        json={
            "apiKey": api_key,
            "timestamp": timestamp,
            "nonce": nonce,
            "signature": signature,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _cached_token = data["token"]
    _token_expiry = time.time() + 86400  # 24h lifetime
    logger.info("RouteStack token acquired")
    return _cached_token


def headers() -> dict:
    return {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
    }
