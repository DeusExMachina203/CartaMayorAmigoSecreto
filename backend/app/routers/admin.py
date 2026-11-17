"""Panel de administración: participantes, configuración y sorteo.

El login de admin va en un router aparte porque no requiere la cookie.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..draw import clear_draw, run_draw
from ..emailer import send_login_code
from ..models import LoginCode, Player, Setting, utcnow
from ..schemas import (
    AdminLogin,
    DrawResultOut,
    PlayerIn,
    PlayerOut,
    PlayerUpdate,
    SettingsIn,
    SettingsOut,
)
from ..security import (
    generate_code,
    hash_code,
    require_admin,
    set_admin_cookie,
)
from .participants import get_settings

# --- Login (sin cookie previa) ---

admin_auth = APIRouter(prefix="/api/admin", tags=["admin"])


@admin_auth.post("/login")
def login(datos: AdminLogin, response: Response, db: Session = Depends(get_db)):
    if datos.password != settings.admin_password:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Contraseña incorrecta")
    set_admin_cookie(response)
    return {"detalle": "Sesión de administrador iniciada"}


@admin_auth.post("/salir")
def salir(response: Response):
    response.delete_cookie("admin_sesion", path="/")
    return {"detalle": "Sesión de administrador cerrada"}


# --- Todo lo demás requiere cookie de admin ---

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/participantes", response_model=list[PlayerOut])
def listar_participantes(db: Session = Depends(get_db)):
    return db.query(Player).order_by(Player.name).all()


@router.post("/participantes", response_model=PlayerOut, status_code=status.HTTP_201_CREATED)
def crear_participante(datos: PlayerIn, db: Session = Depends(get_db)):
    email = datos.email.lower()
    if db.scalar(select(Player).where(Player.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya está registrado")
    player = Player(email=email, name=datos.name)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


@router.patch("/participantes/{player_id}", response_model=PlayerOut)
def editar_participante(
    player_id: int, datos: PlayerUpdate, db: Session = Depends(get_db)
):
    player = _get_player(db, player_id)
    if datos.name is not None:
        player.name = datos.name
    db.commit()
    db.refresh(player)
    return player


@router.delete("/participantes/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_participante(player_id: int, db: Session = Depends(get_db)):
    player = _get_player(db, player_id)
    if db.get(Setting, 1) and db.get(Setting, 1).draw_done:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "No se puede borrar participantes después del sorteo; rehaz el sorteo primero",
        )
    db.delete(player)
    db.commit()


@router.post("/participantes/{player_id}/codigo", status_code=status.HTTP_202_ACCEPTED)
def enviar_codigo(
    player_id: int, background: BackgroundTasks, db: Session = Depends(get_db)
):
    """(Re)envía manualmente un código de acceso a un participante."""
    player = _get_player(db, player_id)
    code = generate_code()
    for old in db.scalars(
        select(LoginCode).where(
            LoginCode.email == player.email, LoginCode.used.is_(False)
        )
    ):
        old.used = True
    db.add(
        LoginCode(
            email=player.email,
            code_hash=hash_code(code),
            expires_at=utcnow() + timedelta(minutes=settings.code_ttl_minutes),
        )
    )
    db.commit()
    background.add_task(send_login_code, player.email, player.name, code)
    return {"detalle": f"Código enviado a {player.email}"}


@router.get("/config", response_model=SettingsOut)
def ver_config(db: Session = Depends(get_db)):
    s = get_settings(db)
    return SettingsOut(
        budget_min=s.budget_min,
        budget_max=s.budget_max,
        event_date=s.event_date,
        draw_done=s.draw_done,
    )


@router.put("/config", response_model=SettingsOut)
def editar_config(datos: SettingsIn, db: Session = Depends(get_db)):
    if datos.budget_min is not None and datos.budget_max is not None:
        if datos.budget_min > datos.budget_max:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El mínimo excede el máximo")
    s = get_settings(db)
    s.budget_min = datos.budget_min
    s.budget_max = datos.budget_max
    s.event_date = datos.event_date
    db.commit()
    db.refresh(s)
    return SettingsOut(
        budget_min=s.budget_min,
        budget_max=s.budget_max,
        event_date=s.event_date,
        draw_done=s.draw_done,
    )


@router.post("/sorteo", response_model=DrawResultOut)
def realizar_sorteo(db: Session = Depends(get_db)):
    """Ejecuta el sorteo entre todos los participantes."""
    s = get_settings(db)
    if s.draw_done:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El sorteo ya se realizó; deshazlo primero si quieres repetirlo",
        )

    player_ids = [p.id for p in db.query(Player).all()]
    try:
        run_draw(db, player_ids)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))

    s.draw_done = True
    s.draw_done_at = utcnow()
    db.commit()
    return DrawResultOut(ok=True, total=len(player_ids))


@router.delete("/sorteo", status_code=status.HTTP_204_NO_CONTENT)
def deshacer_sorteo(db: Session = Depends(get_db)):
    """Deshace el sorteo (por ejemplo, si alguien se apuntó tarde)."""
    clear_draw(db)
    s = get_settings(db)
    s.draw_done = False
    s.draw_done_at = None
    db.commit()


def _get_player(db: Session, player_id: int) -> Player:
    player = db.get(Player, player_id)
    if not player:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participante no encontrado")
    return player
