from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import obtener_sesion
from app.logs import logger
from app.servicios import ForoServicio
from app.gui import obtener_usuario_desde_cookie

router = APIRouter(prefix="/foro", tags=["Foro"])


@router.get("/{curso_slug}/temas")
def obtener_temas(curso_slug: str, sesion: Session = Depends(obtener_sesion)):
    logger.info(f"Obteniendo temas para curso: {curso_slug}")
    from app.servicios import CursoServicio

    curso_servicio = CursoServicio(sesion)
    curso = curso_servicio.obtener_curso_por_slug(curso_slug)
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    foro_servicio = ForoServicio(sesion)
    temas = foro_servicio.obtener_temas_curso(curso.id)
    return {"temas": [{"id": t.id, "titulo": t.titulo, "fecha": t.fecha_creacion} for t in temas]}


@router.post("/{curso_slug}/tema")
def crear_tema(
    curso_slug: str,
    titulo: str,
    contenido: str,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    logger.info(f"Creando tema en curso: {curso_slug}")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario:
        raise HTTPException(status_code=401, detail="No autenticado")

    from app.servicios import CursoServicio

    curso_servicio = CursoServicio(sesion)
    curso = curso_servicio.obtener_curso_por_slug(curso_slug)
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    foro_servicio = ForoServicio(sesion)
    tema = foro_servicio.crear_tema(curso.id, usuario.id, titulo, contenido)
    return {"id": tema.id, "titulo": tema.titulo}


@router.get("/tema/{tema_id}/respuestas")
def obtener_respuestas(tema_id: int, sesion: Session = Depends(obtener_sesion)):
    logger.info(f"Obteniendo respuestas para tema: {tema_id}")
    foro_servicio = ForoServicio(sesion)
    respuestas = foro_servicio.obtener_respuestas(tema_id)
    return {
        "respuestas": [
            {"id": r.id, "contenido": r.contenido, "usuario": r.usuario.nombre} for r in respuestas
        ]
    }


@router.post("/tema/{tema_id}/respuesta")
def crear_respuesta(
    tema_id: int, contenido: str, request: Request, sesion: Session = Depends(obtener_sesion)
):
    logger.info(f"Creando respuesta para tema: {tema_id}")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario:
        raise HTTPException(status_code=401, detail="No autenticado")

    foro_servicio = ForoServicio(sesion)
    respuesta = foro_servicio.crear_respuesta(tema_id, usuario.id, contenido)
    return {"id": respuesta.id}
