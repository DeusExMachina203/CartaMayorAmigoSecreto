"""Mi amigo asignado: revelación individual con clic y vista posterior.

El sorteo completo se genera en secreto con el PRIMER clic que reciba (o
cuando el admin lo lanza); cada participante al tocar "Sortear" solo
revela la asignación que ya le correspondía. Así ningún receptor se
repite, nadie se regala a sí mismo y el último de la fila también
tiene a alguien válido.
"""

from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..draw import get_assignment, run_draw
from ..models import Player, utcnow
from ..schemas import ReceiverOut, WishlistItemOut
from ..security import get_current_player
from .participants import get_settings

router = APIRouter(prefix="/api", tags=["draw"])

# Un solo proceso: evita que dos clics simultáneos creen dos sorteos
_sorteo_lock = Lock()


@router.post("/sortear", response_model=ReceiverOut)
def sortear(db: Session = Depends(get_db), player: Player = Depends(get_current_player)):
    """Revela a quién le regalo yo. Si el sorteo no existe aún, se crea."""
    with _sorteo_lock:
        s = get_settings(db)
        if not s.draw_done:
            player_ids = [p.id for p in db.query(Player).all()]
            try:
                run_draw(db, player_ids)
            except ValueError as exc:
                raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
            s.draw_done = True
            s.draw_done_at = utcnow()
            db.commit()

    assignment = get_assignment(db, player.id)
    if not assignment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No tienes asignación")
    if assignment.revealed_at is None:
        assignment.revealed_at = utcnow()
        db.commit()

    receiver = db.get(Player, assignment.receiver_id)
    return ReceiverOut(
        name=receiver.name,
        wishlist=[WishlistItemOut.model_validate(i) for i in receiver.wishlist],
    )


@router.get("/mi-amigo", response_model=ReceiverOut)
def mi_amigo(db: Session = Depends(get_db), player: Player = Depends(get_current_player)):
    """A quién le regalo yo, con su lista de deseos (tras haber sorteado)."""
    assignment = get_assignment(db, player.id)
    if not assignment or assignment.revealed_at is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Aún no has realizado tu sorteo",
        )
    receiver = db.get(Player, assignment.receiver_id)
    return ReceiverOut(
        name=receiver.name,
        wishlist=[WishlistItemOut.model_validate(i) for i in receiver.wishlist],
    )
