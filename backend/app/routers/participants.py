"""Participantes visibles y configuración pública del evento."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Player, Setting
from ..schemas import ParticipantOut, SettingsOut

router = APIRouter(prefix="/api/participantes", tags=["participants"])


def get_settings(db: Session) -> Setting:
    row = db.get(Setting, 1)
    if not row:
        row = Setting(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("", response_model=list[ParticipantOut])
def listar(db: Session = Depends(get_db)):
    """Lista de participantes confirmados (sin datos sensibles).

    'confirmed' = ya entró al menos una vez (ya tiene lista de deseos creada
    o marcado por el admin). Las asignaciones nunca se exponen aquí.
    """
    players = db.query(Player).order_by(Player.name).all()
    return [
        ParticipantOut(
            id=p.id,
            name=p.name,
            confirmed=any(True for _ in p.wishlist),
        )
        for p in players
    ]


@router.get("/config", response_model=SettingsOut)
def config(db: Session = Depends(get_db)):
    """Presupuesto y fecha visibles para todos."""
    s = get_settings(db)
    return SettingsOut(
        budget_min=s.budget_min,
        budget_max=s.budget_max,
        event_date=s.event_date,
        draw_done=s.draw_done,
    )
