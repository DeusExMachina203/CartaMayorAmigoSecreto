"""Sorteo: asignación tipo derangement (nadie se regala a sí mismo)."""

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Assignment, Player


def run_draw(db: Session, player_ids: list[int]) -> list[Assignment]:
    """Genera una permutación sin puntos fijos (derangement) entre los participantes.

    Lanza ValueError si no es posible (menos de 2 participantes).
    """
    n = len(player_ids)
    if n < 2:
        raise ValueError("Se necesitan al menos 2 participantes para el sorteo")

    # Barajar hasta obtener un derangement (probabilidad esperada de éxito ~1/e
    # por intento; converge rápido incluso con cientos de participantes).
    while True:
        shuffled = player_ids[:]
        for i in range(n - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
        if all(g != r for g, r in zip(player_ids, shuffled)):
            break

    assignments = [Assignment(giver_id=g, receiver_id=r) for g, r in zip(player_ids, shuffled)]
    db.add_all(assignments)
    db.commit()
    return assignments


def get_assignment(db: Session, giver_id: int) -> Assignment | None:
    return db.scalar(select(Assignment).where(Assignment.giver_id == giver_id))


def clear_draw(db: Session) -> int:
    """Borra el sorteo actual. Devuelve cuántas asignaciones se eliminaron."""
    deleted = db.query(Assignment).delete()
    db.commit()
    return deleted
