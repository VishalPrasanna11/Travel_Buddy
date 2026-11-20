"""
Auth0 bearer-token auth. Identity always comes from the token's `sub`
claim, never from a user_email in a request body.

When AUTH0_DOMAIN is set, tokens are verified against the tenant's JWKS
(RS256 signature, issuer, expiry, and audience when AUTH0_AUDIENCE is set).
Without AUTH0_DOMAIN (local dev) tokens are decoded unverified, as before.
"""
import logging
import os
from dataclasses import dataclass
from typing import Optional

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from middlewares.conn_database import get_db
from models.userModel import User

load_dotenv()
logger = logging.getLogger("auth")

AUTH0_DOMAIN = (os.getenv("AUTH0_DOMAIN") or "").replace("https://", "").replace("http://", "").strip("/")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
ALGORITHMS = ["RS256"]

security = HTTPBearer(auto_error=False)
_jwks_client = jwt.PyJWKClient(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json", cache_keys=True) if AUTH0_DOMAIN else None
if not _jwks_client:
    logger.warning("AUTH0_DOMAIN not set: bearer tokens are decoded WITHOUT signature verification")


@dataclass
class Identity:
    sub: str
    email: Optional[str] = None
    claims: Optional[dict] = None

    @property
    def key(self) -> str:
        """Stable per-user key for server-side records."""
        return self.sub


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def decode_token(token: str) -> dict:
    try:
        if _jwks_client:
            signing_key = _jwks_client.get_signing_key_from_jwt(token).key
            return jwt.decode(
                token,
                signing_key,
                algorithms=ALGORITHMS,
                audience=AUTH0_AUDIENCE or None,
                issuer=f"https://{AUTH0_DOMAIN}/",
                options={"verify_aud": bool(AUTH0_AUDIENCE)},
            )
        return jwt.decode(token, options={"verify_signature": False})
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Your session expired. Sign in again.")
    except (jwt.PyJWTError, jwt.PyJWKClientError) as e:
        logger.info(f"Rejected bearer token: {e}")
        raise _unauthorized("Invalid token")


def _email_claim(claims: dict) -> Optional[str]:
    if claims.get("email"):
        return claims["email"]
    for k, v in claims.items():  # Auth0 custom claims are namespaced, e.g. https://app/email
        if k.endswith("/email") and isinstance(v, str):
            return v
    return None


async def optional_identity(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Identity]:
    """Identity if a valid bearer token was sent; None if no token. A bad token is still a 401."""
    if not credentials or not credentials.credentials:
        return None
    claims = decode_token(credentials.credentials)
    sub = claims.get("sub")
    if not sub:
        raise _unauthorized("Invalid token payload")
    ident = Identity(sub=sub, email=_email_claim(claims), claims=claims)
    request.state.identity = ident
    return ident


async def require_identity(ident: Optional[Identity] = Depends(optional_identity)) -> Identity:
    if not ident:
        raise _unauthorized("Sign in to continue.")
    return ident


def resolve_email(ident: Optional[Identity], db: Optional[Session]) -> Optional[str]:
    """Email for legacy email-keyed records: token claim, else the users table."""
    if not ident:
        return None
    if ident.email:
        return ident.email
    if db is None:
        return None
    try:
        user = db.query(User).filter(User.auth0id == ident.sub).first()
        return user.email if user else None
    except Exception as e:
        logger.warning(f"Could not resolve email for {ident.sub}: {e}")
        return None


class Auth:
    """Kept for existing routes (users)."""

    async def verify_jwt(self, ident: Identity = Depends(require_identity)):
        return ident.claims

    async def get_user_from_token(self, ident: Identity = Depends(require_identity), db: Session = Depends(get_db)):
        user = db.query(User).filter(User.auth0id == ident.sub).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return {"user": user, "auth0id": ident.sub}

    async def get_current_user(self, ident: Identity = Depends(require_identity), db: Session = Depends(get_db)):
        return (await self.get_user_from_token(ident, db))["user"]


auth = Auth()
