from app.api.auth import router as auth_router
from app.api.cursos import router as cursos_router
from app.api.webhooks import router as webhooks_router
from app.api.foro import router as foro_router
from app.api.admin import router as admin_router
from app.api.profesor import router as profesor_router
from app.api.coordinador import router as coordinator_router

__all__ = [
    "auth_router",
    "cursos_router",
    "webhooks_router",
    "foro_router",
    "admin_router",
    "profesor_router",
    "coordinator_router",
]
