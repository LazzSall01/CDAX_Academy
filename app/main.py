from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from app.config import obtener_configuracion
from app.logs import logger
from app.database import iniciar_base_datos
from app.modelos import (
    Usuario,
    Curso,
    Modulo,
    Leccion,
    Suscripcion,
    ProgresoLeccion,
    ForoTema,
    ForoRespuesta,
    Material,
    ConfiguracionBunny,
)

from app.api import (
    auth_router,
    cursos_router,
    webhooks_router,
    foro_router,
    admin_router,
    profesor_router,
    coordinator_router,
)
from app.gui.rutas import router as gui_router
from app.gui import inicializar_plantillas

config = obtener_configuracion()

jinja_env = Environment(loader=FileSystemLoader("app/gui/plantillas"))
inicializar_plantillas(jinja_env)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("===========================================")
    logger.info("Iniciando CDAX Academy")
    logger.info(f"Modo: {'DESARROLLO' if config.MODO_DESARROLLO else 'PRODUCCIÓN'}")
    logger.info(f"Base de datos: {config.DATABASE_URL}")
    logger.info("===========================================")
    try:
        iniciar_base_datos()
        logger.info("Base de datos iniciada correctamente")
    except Exception as e:
        logger.error(f"Error al iniciar base de datos: {e}")
    yield
    logger.info("Cerrando CDAX Academy")


app = FastAPI(
    title="CDAX Academy",
    description="Plataforma educativa para odontólogos de élite",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if config.MODO_DESARROLLO else None,
    redoc_url="/redoc" if config.MODO_DESARROLLO else None,
)

# Configuración CORS basada en modo de desarrollo/producción
origenes_permitidos = (
    config.CORS_ORIGINS if config.MODO_DESARROLLO else config.CORS_PRODUCTION_ORIGINS
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origenes_permitidos,
    allow_credentials=config.CORS_ALLOW_CREDENTIALS,
    allow_methods=config.CORS_ALLOW_METHODS,
    allow_headers=config.CORS_ALLOW_HEADERS,
)

static_path = "app/static"
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

app.include_router(auth_router)
app.include_router(cursos_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")
app.include_router(foro_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(profesor_router, prefix="/api")
app.include_router(coordinator_router, prefix="/api")
app.include_router(gui_router)


@app.exception_handler(Exception)
async def manejo_excepciones(request: Request, exc: Exception):
    logger.error(f"Excepción no manejada: {exc}")
    try:
        template = jinja_env.get_template("error.html")
        html = template.render(request=request, codigo=500, mensaje="Error interno del servidor")
    except:
        html = "<html><body><h1>500 Error</h1><p>Error interno del servidor</p></body></html>"
    return HTMLResponse(content=html, status_code=500)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "cdax-academy",
        "mode": "development" if config.MODO_DESARROLLO else "production",
    }


if __name__ == "__main__":
    import uvicorn

    if config.MODO_DESARROLLO:
        print("\n" + "=" * 50)
        print("  DENTAL MODERN ACADEMY - MODO DESARROLLO")
        print("=" * 50)
        print(f"  URL: http://localhost:8000")
        print(f"  Docs: http://localhost:8000/docs")
        print("=" * 50 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=config.MODO_DESARROLLO)
