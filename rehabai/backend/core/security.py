"""Small dependency-free password and JWT primitives for RehabAI."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.db import User, get_db


_DEFAULT_JWT_SECRET = "dev-only-change-this-secret-before-deploying"
JWT_SECRET = os.getenv("JWT_SECRET", "").strip() or _DEFAULT_JWT_SECRET
JWT_TTL_SECONDS = int(os.getenv("JWT_TTL_SECONDS", "86400"))
bearer = HTTPBearer(auto_error=False)

if os.getenv("APP_ENV", "development").lower() in {"production", "prod"} and JWT_SECRET == _DEFAULT_JWT_SECRET:
    raise RuntimeError("JWT_SECRET must be configured in production")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        kind, n, r, p, salt, expected = encoded.split("$")
        if kind != "scrypt":
            return False
        actual = hashlib.scrypt(password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(actual, _unb64(expected))
    except (ValueError, TypeError):
        return False


def create_token(user_id: str) -> str:
    now = int(time.time())
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({"sub": user_id, "iat": now, "exp": now + JWT_TTL_SECONDS}, separators=(",", ":")).encode())
    signature = _b64(hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def decode_token(token: str) -> dict[str, Any]:
    try:
        header, payload, signature = token.split(".")
        expected = _b64(hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        claims = json.loads(_unb64(payload))
        if int(claims.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        return claims
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.") from exc


def user_id_from_token(token: str) -> str:
    user_id = str(decode_token(token).get("sub", "")).strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không có người dùng hợp lệ.")
    return user_id


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập.")
    user = db.get(User, user_id_from_token(credentials.credentials))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại hoặc đã bị khóa.")
    return user


def _require_role(user: User, *roles: str) -> User:
    role = getattr(user, "role", "patient")
    if role not in roles:
        raise HTTPException(status_code=403, detail="Bạn không có quyền thực hiện thao tác này.")
    return user


def doctor_or_admin(
    user: User = Depends(current_user),
) -> User:
    """Dependency for endpoints only doctors or admins may call."""
    return _require_role(user, "doctor", "admin")


def admin_only(
    user: User = Depends(current_user),
) -> User:
    """Dependency for endpoints only admins may call."""
    return _require_role(user, "admin")
