"""Mi amigo asignado (solo visible después del sorteo)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..draw import get_assignment
from ..models import Player
from ..schemas import ReceiverOut, WishlistItemOut
from ..security import get_current_player

router = APIRouter(prefix="/api/mi-amigo", tags=["draw"])


@router.get("", response_model=ReceiverOut)
def mi_amigo(db: Session = Depends(get_db), player: Player = Depends(get_current_player)):
    """A quién le regalo yo, con su lista de deseos. Requiere sorteo hecho."""
    assignment = get_assignment(db, player.id)
    if not assignment:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "El sorteo aún no se ha realizado o no tienes asignación",
        )
    receiver = db.get(Player, assignment.receiver_id)
    return ReceiverOut(
        name=receiver.name,
        wishlist=[WishlistItemOut.model_validate(i) for i in receiver.wishlist],
    )
