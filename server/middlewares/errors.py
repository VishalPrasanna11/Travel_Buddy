"""
Error contract: every response carries X-Request-ID, every error body is
{"error": {code, message, retryable, section, request_id}, "detail": …}.
"""
import logging
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from schemas.api import SCHEMA_VERSION, ErrorBody, new_request_id

logger = logging.getLogger("errors")

STATUS_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "UPSTREAM_ERROR",
    503: "UNAVAILABLE",
    504: "UPSTREAM_TIMEOUT",
}


def request_id_of(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    if not rid:
        rid = request.headers.get("X-Request-ID") or new_request_id()
        request.state.request_id = rid
    return rid


def error_response(
    status: int,
    message: str,
    request_id: str,
    code: Optional[str] = None,
    retryable: Optional[bool] = None,
    section: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    retry_after: Optional[int] = None,
) -> JSONResponse:
    body = ErrorBody(
        code=code or STATUS_CODES.get(status, "ERROR"),
        message=message,
        retryable=retryable if retryable is not None else status in (429, 502, 503, 504),
        section=section,
        request_id=request_id,
        retry_after=retry_after,
    )
    h = {"X-Request-ID": request_id, **(headers or {})}
    if retry_after:
        h["Retry-After"] = str(retry_after)
    return JSONResponse(
        status_code=status,
        content={"error": body.model_dump(exclude_none=True), "detail": message, "schema_version": SCHEMA_VERSION},
        headers=h,
    )


class RequestIdMiddleware:
    """Pure ASGI (no BaseHTTPMiddleware) so SSE streams and disconnects pass through untouched."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        incoming = dict(scope.get("headers") or []).get(b"x-request-id")
        rid = incoming.decode()[:64] if incoming else new_request_id()
        scope.setdefault("state", {})["request_id"] = rid

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                names = {k.lower() for k, _ in headers}
                if b"x-request-id" not in names:
                    headers.append((b"x-request-id", rid.encode()))
                if b"x-schema-version" not in names:
                    headers.append((b"x-schema-version", SCHEMA_VERSION.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_id)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return error_response(exc.status_code, detail, request_id_of(request), headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return error_response(422, "Request body is invalid: " + "; ".join(e.get("msg", "") for e in exc.errors()[:3]), request_id_of(request))

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        rid = request_id_of(request)
        logger.exception(f"Unhandled error ({rid})")
        return error_response(500, "Something went wrong on our side.", rid, retryable=True)


class RateLimiter:
    """Sliding-window limiter, in memory (one dyno). key → recent hit times."""

    def __init__(self, limit: int, window_s: int):
        self.limit = limit
        self.window = window_s
        self.hits: Dict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str) -> Optional[int]:
        """None if allowed, else seconds until the next slot frees up."""
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return max(1, int(self.window - (now - q[0])) + 1)
        q.append(now)
        return None


ask_limiter = RateLimiter(limit=12, window_s=60)
