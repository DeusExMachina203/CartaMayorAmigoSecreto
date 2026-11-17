"""Punto de entrada de la API del Amigo Secreto.

Para desarrollo:
    uvicorn app.main:app --reload

La documentación interactiva queda en http://localhost:8000/docs
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import admin, auth, me, participants, wishlist

logging.basicConfig(level=logging.INFO)

# En desarrollo el frontend (Astro) corre en otro puerto: permitir CORS.
# Las cookies de sesión usan samesite=lax, suficiente para fetch desde el mismo site
# en producción (mismo dominio tras el proxy). En dev se permiten orígenes locales.
app = FastAPI(
    title="Amigo Secreto API",
    description="API para organizar un intercambio de regalos entre amigos 🎁",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4321",  # dev server de Astro
        "http://localhost:8000",
        settings.frontend_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(wishlist.router)
app.include_router(participants.router)
app.include_router(me.router)
app.include_router(admin.admin_auth)
app.include_router(admin.router)


@app.on_event("startup")
def startup() -> None:
    # Prototipo: crea las tablas si no existen. En producción usar Alembic.
    Base.metadata.create_all(engine)


@app.get("/api/salud", tags=["meta"])
def salud():
    return {"estado": "ok", "sorteo": "pendiente de Navidad 🎄"}

