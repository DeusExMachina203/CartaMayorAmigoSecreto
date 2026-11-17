"""Imágenes subidas por los participantes (blobs en la base de datos)."""

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Imagen, Player
from ..security import get_current_player

router = APIRouter(prefix="/api/imagenes", tags=["imagenes"])

# Límite de 50 MB por imagen
MAX_BYTES = 50 * 1024 * 1024


@router.post("", status_code=status.HTTP_201_CREATED)
async def subir_imagen(
    archivo: UploadFile,
    db: Session = Depends(get_db),
    player: Player = Depends(get_current_player),
):
    """Sube una imagen del dispositivo y devuelve su URL para usar en la lista."""
    datos = await archivo.read()
    if len(datos) > MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "La imagen supera el límite de 50 MB",
        )

    mime = archivo.content_type or ""
    if not mime.startswith("image/"):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "El archivo debe ser una imagen",
        )
    if not datos:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Archivo vacío")

    imagen = Imagen(mime=mime, data=datos)
    db.add(imagen)
    db.commit()
    db.refresh(imagen)
    return {"id": imagen.id, "url": f"/api/imagenes/{imagen.id}"}


@router.get("/{imagen_id}")
def ver_imagen(imagen_id: int, db: Session = Depends(get_db)):
    """Sirve la imagen (con caché; las URLs no cambian)."""
    imagen = db.get(Imagen, imagen_id)
    if not imagen:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Imagen no encontrada")
    return Response(
        content=imagen.data,
        media_type=imagen.mime,
        headers={"Cache-Control": "public, max-age=86400"},
    )
