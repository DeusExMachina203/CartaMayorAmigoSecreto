"""Lista de deseos del participante autenticado."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..enrichment import extract_asin, fetch_product_info
from ..models import Player, WishlistItem
from ..schemas import EnrichOut, EnrichRequest, WishlistItemIn, WishlistItemOut
from ..security import get_current_player

router = APIRouter(prefix="/api/mi-lista", tags=["wishlist"])


@router.get("", response_model=list[WishlistItemOut])
def mi_lista(db: Session = Depends(get_db), player: Player = Depends(get_current_player)):
    return db.query(WishlistItem).filter(WishlistItem.player_id == player.id).all()


@router.post("", response_model=WishlistItemOut, status_code=status.HTTP_201_CREATED)
def agregar_item(
    datos: WishlistItemIn, db: Session = Depends(get_db), player: Player = Depends(get_current_player)
):
    item = WishlistItem(
        player_id=player.id,
        name=datos.name,
        notes=datos.notes,
        price_hint=datos.price_hint,
        image_url=datos.image_url,
        amazon_url=datos.amazon_url,
        asin=extract_asin(datos.amazon_url) if datos.amazon_url else "",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=WishlistItemOut)
def editar_item(
    item_id: int,
    datos: WishlistItemIn,
    db: Session = Depends(get_db),
    player: Player = Depends(get_current_player),
):
    item = _own_item(db, player, item_id)
    item.name = datos.name
    item.notes = datos.notes
    item.price_hint = datos.price_hint
    item.image_url = datos.image_url
    item.amazon_url = datos.amazon_url
    item.asin = extract_asin(datos.amazon_url) if datos.amazon_url else ""
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_item(
    item_id: int, db: Session = Depends(get_db), player: Player = Depends(get_current_player)
):
    item = _own_item(db, player, item_id)
    db.delete(item)
    db.commit()


@router.post("/enriquecer", response_model=EnrichOut)
def enriquecer(
    datos: EnrichRequest,
    background: BackgroundTasks,
    player: Player = Depends(get_current_player),
):
    """Intenta autocompletar nombre e imagen desde un enlace de Amazon.

    Es best-effort: puede fallar silenciosamente (Amazon bloquea bots);
    el usuario siempre puede completar los campos a mano.
    """
    info = fetch_product_info(datos.url)
    return EnrichOut(**info)


def _own_item(db: Session, player: Player, item_id: int) -> WishlistItem:
    item = db.get(WishlistItem, item_id)
    if not item or item.player_id != player.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Regalo no encontrado")
    return item
