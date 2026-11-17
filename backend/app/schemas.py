"""Esquemas Pydantic de entrada/salida de la API."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

# ---------- Auth ----------


class CodeRequest(BaseModel):
    email: EmailStr


class CodeVerify(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class MeOut(BaseModel):
    id: int
    email: str
    name: str
    is_admin: bool


# ---------- Lista de deseos ----------


class WishlistItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    notes: str = ""
    price_hint: str = Field(default="", max_length=50)
    image_url: str = ""
    amazon_url: str = ""


class WishlistItemOut(BaseModel):
    id: int
    name: str
    notes: str
    price_hint: str
    image_url: str
    amazon_url: str
    asin: str

    model_config = {"from_attributes": True}


class EnrichRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000)


class EnrichOut(BaseModel):
    name: str = ""
    image_url: str = ""
    asin: str = ""


# ---------- Participantes ----------


class ParticipantOut(BaseModel):
    id: int
    name: str
    confirmed: bool  # ya entró alguna vez (tiene wishlist o sesión)

    model_config = {"from_attributes": True}


class SettingsOut(BaseModel):
    budget_min: float | None
    budget_max: float | None
    event_date: str
    draw_done: bool


# ---------- Amigo asignado ----------


class ReceiverOut(BaseModel):
    name: str
    wishlist: list[WishlistItemOut]


# ---------- Admin ----------


class AdminLogin(BaseModel):
    password: str


class PlayerIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)


class PlayerUpdate(BaseModel):
    name: str | None = None


class PlayerOut(PlayerIn):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SettingsIn(BaseModel):
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    event_date: str = ""


class DrawResultOut(BaseModel):
    ok: bool
    total: int
