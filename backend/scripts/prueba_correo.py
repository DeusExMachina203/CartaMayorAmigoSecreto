"""Prueba el envío de correo con la configuración SMTP del .env.

Uso:
    .venv/bin/python scripts/prueba_correo.py tu@correo.com

Envía un correo de prueba a la dirección indicada y reporta si funcionó.
"""

import smtplib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings  # noqa: E402
from app.emailer import send_login_code  # noqa: E402


class DebugSMTP(smtplib.SMTP):
    """Activa la conversación SMTP completa para diagnóstico."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_debuglevel(2)


def main():
    if len(sys.argv) < 2:
        print("Uso: .venv/bin/python scripts/prueba_correo.py TU@CORREO.COM")
        sys.exit(1)

    destino = sys.argv[1]

    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_token:
        print("❌ Falta configuración SMTP en backend/.env:")
        print("   SMTP_HOST, SMTP_USER, SMTP_TOKEN (y SMTP_FROM)")
        sys.exit(1)

    # Conectar con la conversación SMTP visible para diagnóstico
    import app.emailer as emailer_mod

    emailer_mod.smtplib.SMTP = DebugSMTP

    print(f"Servidor : {settings.smtp_host}:{settings.smtp_port}")
    print(f"Usuario  : {settings.smtp_user}")
    print(f"De       : {settings.smtp_from or settings.smtp_user}")
    print(f"Para     : {destino}")
    print("Enviando...")

    try:
        send_login_code(destino, "Dex", "123456")
        print()
        print("✅ ¡Correo enviado! Revisa la bandeja (y el spam) de", destino)
        print("   También debería aparecer en la carpeta Enviados de Proton.")
    except Exception as exc:
        print()
        print(f"❌ Falló el envío: {exc}")
        print()
        print("Pistas comunes:")
        print("  - ¿El token SMTP es el correcto? (no es la contraseña de la cuenta)")
        print("  - ¿SMTP_FROM es exactamente la dirección asociada al token?")
        print("  - ¿Tu red/firewall bloquea el puerto 587 saliente?")
        sys.exit(1)


if __name__ == "__main__":
    main()
