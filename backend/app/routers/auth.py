"""Autenticación por código de acceso enviado por correo."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..emailer import send_login_code
from ..models import LoginCode, utcnow
from ..schemas import CodeRequest, CodeVerify, MeOut
from ..security import (
    clear_session_cookie,
    email_belongs_to_player,
    generate_code,
    get_current_player,
    get_optional_player,
    hash_code,
    set_session_cookie,
    verify_code_hash,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/solicitar-codigo", status_code=status.HTTP_202_ACCEPTED)
def solicitar_codigo(
    datos: CodeRequest, background: BackgroundTasks, db: Session = Depends(get_db)
):
    """Envía un código de 6 dígitos al correo indicado (si está registrado).

    Responde 202 siempre, aunque el correo no exista, para no filtrar qué
    correos están registrados.
    """
    email = datos.email.lower()
    player = email_belongs_to_player(db, email)

    # Enfriamiento solo si el último código sigue sin usarse y es reciente:
    # si ya se usó o venció, puede pedirse otro de inmediato.
    last = db.scalar(
        select(LoginCode).where(LoginCode.email == email).order_by(LoginCode.id.desc())
    )
    if (
        last
        and not last.used
        and last.expires_at > utcnow()
        and (utcnow() - last.created_at).total_seconds() < settings.code_resend_cooldown
    ):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Espera {settings.code_resend_cooldown} segundos antes de pedir otro código",
        )

    # Un solo código activo por correo: los anteriores quedan usados
    if player:
        for old in db.scalars(
            select(LoginCode).where(LoginCode.email == email, LoginCode.used.is_(False))
        ):
            old.used = True

        code = generate_code()
        login_code = LoginCode(
            email=email,
            code_hash=hash_code(code),
            expires_at=utcnow() + timedelta(minutes=settings.code_ttl_minutes),
        )
        db.add(login_code)
        db.commit()

        # El envío por SMTP se hace fuera del ciclo de la respuesta
        background.add_task(send_login_code, email, player.name, code)

    return {"detalle": "Si el correo está registrado, recibirás un código."}


@router.post("/verificar", response_model=MeOut)
def verificar(datos: CodeVerify, response: Response, db: Session = Depends(get_db)):
    """Canjea el código por una sesión (cookie JWT)."""
    email = datos.email.lower()
    player = email_belongs_to_player(db, email)
    if not player:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Código incorrecto")

    login_code = db.scalar(
        select(LoginCode)
        .where(LoginCode.email == email, LoginCode.used.is_(False))
        .order_by(LoginCode.id.desc())
    )
    if (
        not login_code
        or login_code.expires_at < utcnow()
        or login_code.attempts >= settings.code_max_attempts
        or not verify_code_hash(datos.code, login_code.code_hash)
    ):
        if login_code:
            login_code.attempts += 1
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Código incorrecto o vencido")

    login_code.used = True
    db.commit()
    set_session_cookie(response, player)
    return player


@router.post("/salir")
def salir(response: Response):
    clear_session_cookie(response)
    return {"detalle": "Sesión cerrada"}


@router.get("/yo", response_model=MeOut)
def yo(player: Player = Depends(get_current_player)):
    return player


@router.get("/estado")
def estado(player=Depends(get_optional_player)):
    """Indica si hay sesión válida (para el frontend al cargar)."""
    return {"autenticado": player is not None}
