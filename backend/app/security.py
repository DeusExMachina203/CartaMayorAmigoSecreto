"""Utilidades de seguridad: JWT, hashing de códigos y dependencias de autenticación."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Player

SESSION_COOKIE = "sesion"
ADMIN_COOKIE = "admin_sesion"
ALGORITHM = "HS256"


# ---------- Tokens JWT ----------


def _create_token(payload: dict, days: int) -> str:
    to_encode = payload.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(days=days)
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def _decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida o expirada")
    if payload.get("typ") != expected_type:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida")
    return payload


def set_session_cookie(response: Response, player: Player) -> None:
    token = _create_token({"sub": str(player.id), "typ": "user"}, settings.session_days)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=False,  # en producción (HTTPS) cambiar a True
        samesite="lax",
        max_age=settings.session_days * 24 * 3600,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


def set_admin_cookie(response: Response) -> None:
    token = _create_token({"typ": "admin"}, 1)
    response.set_cookie(
        ADMIN_COOKIE,
        token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=24 * 3600,
        path="/",
    )


def is_admin(request: Request) -> bool:
    token = request.cookies.get(ADMIN_COOKIE)
    if not token:
        return False
    try:
        _decode_token(token, "admin")
        return True
    except HTTPException:
        return False


# ---------- Códigos de acceso ----------


def generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_code(code: str) -> str:
    # HMAC con la secret key: un hash simple pero con clave, suficiente para
    # códigos de 6 dígitos de vida corta.
    return hmac.new(
        settings.secret_key.encode(), code.encode(), hashlib.sha256
    ).hexdigest()


def verify_code_hash(code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_code(code), code_hash)


# ---------- Dependencias ----------


def get_current_player(
    request: Request, db: Session = Depends(get_db)
) -> Player:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No has iniciado sesión")
    payload = _decode_token(token, "user")
    player = db.get(Player, int(payload["sub"]))
    if not player:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Participante no encontrado")
    return player


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autorizado")


def get_optional_player(request: Request, db: Session = Depends(get_db)) -> Player | None:
    """Como get_current_player, pero devuelve None en vez de fallar."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        payload = _decode_token(token, "user")
        return db.get(Player, int(payload["sub"]))
    except HTTPException:
        return None


def email_belongs_to_player(db: Session, email: str) -> Player | None:
    return db.scalar(select(Player).where(Player.email == email.lower()))
