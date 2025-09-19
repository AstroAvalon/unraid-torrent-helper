# ==============================
# app/auth.py
# ==============================
from __future__ import annotations

import time
import hmac
import bcrypt
import hashlib
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import AppConfig
from .db import DB
from .models import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Session cookie config (simple HMAC-signed token)
COOKIE_NAME = "uth_session"
TOKEN_TTL = 24 * 3600  # 24 hours

# Optional Bearer token support (for CLI/scripts)
security = HTTPBearer(auto_error=False)


def sign_token(secret: str, username: str, exp: int) -> str:
    payload = f"{username}:{exp}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def verify_token(secret: str, token: str) -> Optional[str]:
    try:
        username, exp_s, sig = token.rsplit(":", 2)
        exp = int(exp_s)
        payload = f"{username}:{exp}"
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        if time.time() > exp:
            return None
        return username
    except Exception:
        return None


def ensure_admin_user(db: DB, cfg: AppConfig) -> None:
    row = db.conn.execute(
        "SELECT id FROM users WHERE username=?",
        (cfg.init_admin_user,),
    ).fetchone()
    if row is None:
        pw_hash = bcrypt.hashpw(cfg.init_admin_pass.encode(), bcrypt.gensalt()).decode()
        db.conn.execute(
            "INSERT INTO users(username,password_hash) VALUES(?,?)",
            (cfg.init_admin_user, pw_hash),
        )
        db.conn.commit()


@router.post("/login")
def login(req: Request, body: LoginRequest) -> Response:
    # Pull app state
    db: DB = req.app.state.db
    cfg: AppConfig = req.app.state.cfg

    # Ensure bootstrap admin exists
    ensure_admin_user(db, cfg)

    # Lookup user
    row = db.conn.execute(
        "SELECT password_hash FROM users WHERE username=?",
        (body.username,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    stored = row["password_hash"]
    stored_bytes = stored.encode() if isinstance(stored, str) else stored
    if not bcrypt.checkpw(body.password.encode(), stored_bytes):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Issue signed cookie
    exp = int(time.time()) + TOKEN_TTL
    token = sign_token(cfg.secret_key, body.username, exp)

    resp = Response(status_code=204)
    # Set cookie (for production behind reverse proxy, set secure=True)
    resp.set_cookie(
        COOKIE_NAME,
        token,
        max_age=TOKEN_TTL,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return resp


@router.post("/logout")
def logout() -> Response:
    resp = Response(status_code=204)
    resp.delete_cookie(COOKIE_NAME)
    return resp


def auth_guard(
    req: Request,
    authz: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """
    Returns the authenticated username or raises 401.
    Order:
      1) Cookie session (primary)
      2) Bearer token (optional for CLI)
    """
    cfg: AppConfig = req.app.state.cfg

    # 1) Cookie
    token = req.cookies.get(COOKIE_NAME)
    if token:
        user = verify_token(cfg.secret_key, token)
        if user:
            return user

    # 2) Bearer (Authorization: Bearer <token>)
    if authz:
        user = verify_token(cfg.secret_key, authz.credentials)
        if user:
            return user

    raise HTTPException(status_code=401, detail="Unauthorized")