import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Configuracion(BaseSettings):
    # Base de datos
    DATABASE_URL: str = "sqlite:///./dental_academia.db"
    REDIS_URL: str = "redis://localhost:6379"

    # Seguridad
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    MODO_DESARROLLO: bool = True

    # Dominio
    DOMAIN: str = "https://pmn8x3l7-8000.usw3.devtunnels.ms"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_USER_INFO_URL: str = "https://www.googleapis.com/oauth2/v2/userinfo"

    # Stripe
    STRIPE_PUBLIC_KEY: str = "pk_test_51Sv8MrRGI5ZSN6ze6dJtVDqieyshWYHcfMWueoSmLU30seqeSc2lZpOYHAX4tbSWukN4rohN5AtHiRedopZAFn0o00URE7rkbg"
    STRIPE_SECRET_KEY: str = "sk_test_51Sv8MrRGI5ZSN6ze6dJtVDqieyshWYHcfMWueoSmLU30seqeSc2lZpOYHAX4tbSWukN4rohN5AtHiRedopZAFn0o00URE7rkbg"
    STRIPE_WEBHOOK_SECRET: str = ""

    # CDAX - Información de contacto
    DIRECCION_CDAX: str = "Centro JV Torre Mayor, Oficina 8-G, Pastoresa, Xalapa, Veracruz"
    EMAIL_CDAX: str = "info@cdaxacademy.com"
    WHATSAPP_NUMERO: str = "5215530000000"
    WHATSAPP_MENSAJE_DEFAULT: str = (
        "Hola, me interesa obtener información sobre los programas de CDAX Academy"
    )
    HORARIO_ATENCION: str = "Lun - Vie: 9:00 a 18:00"

    # Bunny Stream & CDN
    BUNNY_API_KEY: str = "45181e55-43ec-4b34-81d4186fa445-a26a-46f4"
    BUNNY_LIBRARY_ID: str = "632570"
    BUNNY_STORAGE_ZONE: str = "cdaxacademy"
    BUNNY_HOSTNAME: str = "localhost:8000"

    # CORS - Configuración de orígenes permitidos
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # Producción
    CORS_PRODUCTION_ORIGINS: list[str] = []  # TODO: Agregar dominio de producción
    SECRET_KEY_PRODUCTION: str = ""  # TODO: Generar clave segura

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.GOOGLE_REDIRECT_URI:
            self.GOOGLE_REDIRECT_URI = f"https://{self.DOMAIN}/auth/google/callback"

    @property
    def whatsapp_link(self) -> str:
        return f"https://wa.me/52{self.WHATSAPP_NUMERO}"


@lru_cache()
def obtener_configuracion() -> Configuracion:
    return Configuracion()
