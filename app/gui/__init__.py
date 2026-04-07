from fastapi import Request, Depends
from sqlalchemy.orm import Session
from app.database import obtener_sesion
from app.logs import logger
from app.config import obtener_configuracion
from fastapi.responses import HTMLResponse

config = obtener_configuracion()

jinja_env = None


def inicializar_plantillas(env):
    global jinja_env
    jinja_env = env


def obtener_usuario_desde_cookie(request: Request, sesion: Session = Depends(obtener_sesion)):
    from app.servicios import AuthServicio

    token = request.cookies.get("session_token")
    if not token:
        return None
    try:
        auth_servicio = AuthServicio(sesion)
        return auth_servicio.obtener_usuario_actual(token)
    except:
        return None


def renderizar(request: Request, plantilla: str, contexto: dict):
    contexto_final = {
        "domain": config.DOMAIN,
        "config": config,
    }

    if "usuario" in contexto:
        contexto_final["usuario"] = contexto["usuario"]
    else:
        contexto_final["usuario"] = None

    for key, value in contexto.items():
        if key not in contexto_final:
            contexto_final[key] = value

    template = jinja_env.get_template(plantilla)
    html = template.render(request=request, **contexto_final)
    return HTMLResponse(content=html)


async def pagina_error(request: Request, codigo: int, mensaje: str):
    logger.error(f"Error {codigo}: {mensaje}")
    try:
        template = jinja_env.get_template("error.html")
        html = template.render(request=request, codigo=codigo, mensaje=mensaje)
    except:
        html = f"<html><body><h1>{codigo}</h1><p>{mensaje}</p></body></html>"
    return HTMLResponse(content=html, status_code=codigo)
