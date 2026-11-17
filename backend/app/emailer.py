"""Envío del código de acceso por correo.

Dos modos:
- SMTP real (Proton): si SMTP_HOST está configurado.
- Consola: si no, imprime el código en el log del servidor (desarrollo).
"""

import logging
import smtplib
from email.message import EmailMessage

from .config import settings

logger = logging.getLogger("amigosecreto.email")

PLANTILLA_CODIGO = """\
Hola {nombre}:

Tu código para entrar al Amigo Secreto es:

    {codigo}

Este código vence en {minutos} minutos y solo puede usarse una vez.

Si no solicitaste este código, ignora este mensaje.
"""


def send_login_code(email: str, nombre: str, codigo: str) -> None:
    """Envía el código por SMTP o lo imprime en consola. Bloqueante."""
    if not settings.smtp_host:
        logger.warning(
            "[DEV] Código para %s (%s): %s (SMTP no configurado, no se envió correo)",
            email,
            nombre,
            codigo,
        )
        return

    msg = EmailMessage()
    msg["Subject"] = "Tu código para el Amigo Secreto 🎁"
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = email
    msg.set_content(
        PLANTILLA_CODIGO.format(nombre=nombre, codigo=codigo, minutos=settings.code_ttl_minutes)
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_token)
        smtp.send_message(msg)
    logger.info("Código enviado a %s vía SMTP", email)
