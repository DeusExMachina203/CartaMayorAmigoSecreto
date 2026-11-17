"""Modelos de la base de datos."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    # UTC sin zona: SQLite no conserva la zona horaria y mezclar aware/naive
    # al comparar rompe. Guardamos siempre UTC "ingenuo".
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Player(Base):
    """Participante del Amigo Secreto."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    wishlist: Mapped[list["WishlistItem"]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )


class LoginCode(Base):
    """Código de un solo uso enviado por correo para iniciar sesión."""

    __tablename__ = "login_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    code_hash: Mapped[str] = mapped_column(String(255))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class WishlistItem(Base):
    """Un regalo deseados por un participante."""

    __tablename__ = "wishlist_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    # Detalles opcionales: talla, color, tienda alternativa, etc.
    notes: Mapped[str] = mapped_column(Text, default="")
    # Precio de referencia en soles (opcional)
    price_hint: Mapped[str] = mapped_column(String(50), default="")
    image_url: Mapped[str] = mapped_column(Text, default="")
    amazon_url: Mapped[str] = mapped_column(Text, default="")
    # ASIN extraído del enlace de Amazon (para enriquecimiento futuro con la API)
    asin: Mapped[str] = mapped_column(String(10), default="")

    player: Mapped["Player"] = relationship(back_populates="wishlist")


class Assignment(Base):
    """Resultado del sorteo: quién regala a quién."""

    __tablename__ = "assignments"
    __table_args__ = (UniqueConstraint("giver_id", name="uq_giver_once"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    giver_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), unique=True)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Setting(Base):
    """Configuración del evento (una sola fila, id=1)."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)  # siempre 1
    # Código de invitación para registrarse (viaja en el enlace que comparte el admin)
    invite_code: Mapped[str] = mapped_column(String(50), default="")
    budget_min: Mapped[float | None] = mapped_column(default=None)
    budget_max: Mapped[float | None] = mapped_column(default=None)
    # Fecha límite para unirse / fecha del intercambio
    event_date: Mapped[str] = mapped_column(String(10), default="")  # ISO: YYYY-MM-DD
    draw_done: Mapped[bool] = mapped_column(Boolean, default=False)
    draw_done_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
