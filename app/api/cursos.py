from fastapi import APIRouter, Depends, HTTPException, Cookie, Request
from sqlalchemy.orm import Session
from app.database import obtener_sesion
from app.logs import logger
from app.servicios import AuthServicio, CursoServicio
from app.config import obtener_configuracion

router = APIRouter(prefix="/cursos", tags=["Cursos"])
config = obtener_configuracion()


def obtener_usuario_desde_cookie(request: Request, sesion: Session = Depends(obtener_sesion)):
    token = request.cookies.get("session_token")
    if not token:
        logger.warning("Token no encontrado en cookies")
        raise HTTPException(status_code=401, detail="No autenticado")

    auth_servicio = AuthServicio(sesion)
    try:
        usuario = auth_servicio.obtener_usuario_actual(token)
        return usuario
    except Exception as e:
        logger.error(f"Error al obtener usuario: {e}")
        raise HTTPException(status_code=401, detail="Token inválido")


@router.get("/")
def listar_cursos(sesion: Session = Depends(obtener_sesion)):
    logger.info("Listando todos los cursos")
    servicio = CursoServicio(sesion)
    cursos = servicio.obtener_todos_los_cursos()
    return {
        "cursos": [
            {"id": c.id, "titulo": c.titulo, "slug": c.slug, "precio": c.precio} for c in cursos
        ]
    }


@router.get("/{slug}")
def obtener_curso(slug: str, sesion: Session = Depends(obtener_sesion)):
    logger.info(f"Obteniendo curso: {slug}")
    servicio = CursoServicio(sesion)
    curso = servicio.obtener_curso_por_slug(slug)
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return {
        "id": curso.id,
        "titulo": curso.titulo,
        "descripcion": curso.descripcion,
        "precio": curso.precio,
        "imagen_url": curso.imagen_url,
    }


@router.post("/{curso_id}/comprar")
def comprar_curso(curso_id: int, request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info(f"Iniciando compra para curso {curso_id}")
    usuario = obtener_usuario_desde_cookie(request, sesion)
    servicio = CursoServicio(sesion)
    url_pago = servicio.crear_sesion_stripe_checkout(
        curso_id=curso_id, usuario_id=usuario.id, dominio=f"https://{config.DOMAIN}"
    )
    return {"url": url_pago}
