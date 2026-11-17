"""Configuración central de la aplicación, leída de variables de entorno (.env)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Seguridad
    secret_key: str = "dev-secret-key-no-usar-en-produccion"
    admin_password: str = "admin-dev"

    # Correo SMTP (Proton). Si smtp_host está vacío, los códigos van a la consola.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_token: str = ""
    smtp_from: str = ""

    # Aplicación
    frontend_url: str = "http://localhost:4321"
    database_url: str = "sqlite:///data/app.db"

    # Vigencia del código de acceso, en minutos
    code_ttl_minutes: int = 15
    # Intentos permitidos por código
    code_max_attempts: int = 5
    # Segundos de espera entre solicitudes de código para el mismo correo
    code_resend_cooldown: int = 60
    # Días que dura la sesión (cookie JWT)
    session_days: int = 30


settings = Settings()
