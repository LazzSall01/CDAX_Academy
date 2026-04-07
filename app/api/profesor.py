from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import obtener_sesion
from app.logs import logger
from app.modelos import Usuario, RolUsuario, Curso, Modulo, Leccion
from app.servicios.auth_servicio import AuthServicio
from app.servicios.bunny_stream_servicio import BunnyStreamServicio
from app.config import obtener_configuracion

router = APIRouter(prefix="/profesor", tags=["Profesor"])
config = obtener_configuracion()


def verificar_profesor(request: Request, sesion: Session = Depends(obtener_sesion)):
    """Middleware para verificar que el usuario es PROFESOR"""
    from app.gui import obtener_usuario_desde_cookie

    usuario = obtener_usuario_desde_cookie(request, sesion)
    if not usuario or usuario.rol not in [RolUsuario.ADMIN, RolUsuario.PROFESOR]:
        logger.warning(f"Acceso denegado a /profesor")
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requiere rol de profesor.")
    return usuario


@router.get("/dashboard")
def dashboard(request: Request, sesion: Session = Depends(obtener_sesion)):
    """Dashboard del profesor"""
    usuario = verificar_profesor(request, sesion)

    # Cursos del profesor
    from app.modelos import CursoInstructor

    cursos_ids = (
        sesion.query(CursoInstructor.curso_id)
        .filter(CursoInstructor.usuario_id == usuario.id)
        .all()
    )
    cursos_ids = [c[0] for c in cursos_ids]

    mis_cursos = sesion.query(Curso).filter(Curso.id.in_(cursos_ids)).all() if cursos_ids else []

    # También cursos donde es instructor
    instructor_cursos = (
        sesion.query(Curso)
        .join(CursoInstructor)
        .filter(CursoInstructor.usuario_id == usuario.id)
        .all()
    )

    return {
        "usuario": usuario,
        "mis_cursos": [
            {
                "id": c.id,
                "titulo": c.titulo,
                "slug": c.slug,
                "tipo_programa": c.tipo_programa,
                "estado_inscripcion": c.estado_inscripcion,
                "precio": c.precio,
            }
            for c in instructor_cursos
        ],
    }


class CrearCursoRequest(BaseModel):
    titulo: str
    descripcion: str
    precio: int
    duracion_horas: int = None
    modalidad: str = "EN_LINEA"
    incluye_diploma: bool = True
    incluye_materiales: bool = True
    requisitos_admision: str = None


@router.post("/cursos")
def crear_curso(
    data: CrearCursoRequest, request: Request, sesion: Session = Depends(obtener_sesion)
):
    """Crear un nuevo curso (solo tipo CURSO para profesores)"""
    usuario = verificar_profesor(request, sesion)

    from slugify import slugify
    from app.modelos import CursoInstructor

    # Verificar que no existe el slug
    slug = slugify(data.titulo)
    existente = sesion.query(Curso).filter(Curso.slug == slug).first()
    if existente:
        slug = f"{slug}-{usuario.id}"

    # Crear curso
    curso = Curso(
        titulo=data.titulo,
        slug=slug,
        descripcion=data.descripcion,
        precio=data.precio,
        tipo_programa="CURSO",  # Forzado para profesores
        duracion_horas=data.duracion_horas,
        modalidad=data.modalidad,
        incluye_diploma=data.incluye_diploma,
        incluye_materiales=data.incluye_materiales,
        requisitos_admision=data.requisitos_admision,
        estado_inscripcion="PROXIMAMENTE",
        activo=True,
    )
    sesion.add(curso)
    sesion.flush()

    # Asignar profesor al curso
    curso_instructor = CursoInstructor(
        curso_id=curso.id,
        usuario_id=usuario.id,
    )
    sesion.add(curso_instructor)
    sesion.commit()

    logger.info(f"Curso creado por profesor {usuario.email}: {curso.titulo}")
    return {"success": True, "curso_id": curso.id, "slug": curso.slug}


@router.get("/cursos/{curso_id}")
def ver_curso(curso_id: int, request: Request, sesion: Session = Depends(obtener_sesion)):
    """Ver detalles de un curso"""
    usuario = verificar_profesor(request, sesion)

    from app.modelos import CursoInstructor

    es_propietario = (
        sesion.query(CursoInstructor)
        .filter(CursoInstructor.curso_id == curso_id, CursoInstructor.usuario_id == usuario.id)
        .first()
    )

    if not es_propietario:
        raise HTTPException(status_code=403, detail="No tienes acceso a este curso")

    curso = sesion.query(Curso).filter(Curso.id == curso_id).first()
    modulos = sesion.query(Modulo).filter(Modulo.curso_id == curso_id).order_by(Modulo.orden).all()

    return {
        "curso": {
            "id": curso.id,
            "titulo": curso.titulo,
            "descripcion": curso.descripcion,
            "precio": curso.precio,
            "tipo_programa": curso.tipo_programa,
            "estado_inscripcion": curso.estado_inscripcion,
            "imagen_url": curso.imagen_url,
        },
        "modulos": [
            {
                "id": m.id,
                "titulo": m.titulo,
                "orden": m.orden,
                "lecciones": [
                    {
                        "id": l.id,
                        "titulo": l.titulo,
                        "duracion_minutos": l.duracion_minutos,
                        "estado_video": l.estado_video,
                        "tipo_video": l.tipo_video,
                    }
                    for l in m.lecciones
                ],
            }
            for m in modulos
        ],
    }


class ActualizarCursoRequest(BaseModel):
    titulo: str = None
    descripcion: str = None
    precio: int = None
    estado_inscripcion: str = None
    imagen_url: str = None


@router.put("/cursos/{curso_id}")
def actualizar_curso(
    curso_id: int,
    data: ActualizarCursoRequest,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """Actualizar un curso"""
    usuario = verificar_profesor(request, sesion)

    from app.modelos import CursoInstructor

    es_propietario = (
        sesion.query(CursoInstructor)
        .filter(CursoInstructor.curso_id == curso_id, CursoInstructor.usuario_id == usuario.id)
        .first()
    )

    if not es_propietario:
        raise HTTPException(status_code=403, detail="No tienes acceso a este curso")

    curso = sesion.query(Curso).filter(Curso.id == curso_id).first()

    if data.titulo is not None:
        curso.titulo = data.titulo
    if data.descripcion is not None:
        curso.descripcion = data.descripcion
    if data.precio is not None:
        curso.precio = data.precio
    if data.estado_inscripcion is not None:
        curso.estado_inscripcion = data.estado_inscripcion
    if data.imagen_url is not None:
        curso.imagen_url = data.imagen_url

    sesion.commit()

    logger.info(f"Curso actualizado: {curso.titulo}")
    return {"success": True}


class CrearModuloRequest(BaseModel):
    titulo: str
    orden: int


@router.post("/cursos/{curso_id}/modulos")
def crear_modulo(
    curso_id: int,
    data: CrearModuloRequest,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """Crear un módulo en un curso"""
    usuario = verificar_profesor(request, sesion)

    from app.modelos import CursoInstructor

    es_propietario = (
        sesion.query(CursoInstructor)
        .filter(CursoInstructor.curso_id == curso_id, CursoInstructor.usuario_id == usuario.id)
        .first()
    )

    if not es_propietario:
        raise HTTPException(status_code=403, detail="No tienes acceso a este curso")

    modulo = Modulo(
        curso_id=curso_id,
        titulo=data.titulo,
        orden=data.orden,
    )
    sesion.add(modulo)
    sesion.commit()

    logger.info(f"Módulo creado: {data.titulo}")
    return {"success": True, "modulo_id": modulo.id}


class CrearLeccionRequest(BaseModel):
    modulo_id: int
    titulo: str
    descripcion: str = None
    duracion_minutos: int = 0
    orden: int


@router.post("/cursos/{curso_id}/lecciones")
def crear_leccion(
    curso_id: int,
    data: CrearLeccionRequest,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """Crear una lección en un módulo"""
    usuario = verificar_profesor(request, sesion)

    from app.modelos import CursoInstructor

    es_propietario = (
        sesion.query(CursoInstructor)
        .filter(CursoInstructor.curso_id == curso_id, CursoInstructor.usuario_id == usuario.id)
        .first()
    )

    if not es_propietario:
        raise HTTPException(status_code=403, detail="No tienes acceso a este curso")

    leccion = Leccion(
        modulo_id=data.modulo_id,
        titulo=data.titulo,
        descripcion=data.descripcion,
        duracion_minutos=data.duracion_minutos,
        orden=data.orden,
        estado_video="SIN_SUBIR",
        tipo_video="BUNNY",
    )
    sesion.add(leccion)
    sesion.commit()

    logger.info(f"Lección creada: {data.titulo}")
    return {"success": True, "leccion_id": leccion.id}


@router.post("/cursos/{curso_id}/lecciones/{leccion_id}/video")
async def subir_video(
    curso_id: int,
    leccion_id: int,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
    archivo: UploadFile = File(...),
):
    """Subir video de una lección a Bunny Stream"""
    usuario = verificar_profesor(request, sesion)

    from app.modelos import CursoInstructor

    es_propietario = (
        sesion.query(CursoInstructor)
        .filter(CursoInstructor.curso_id == curso_id, CursoInstructor.usuario_id == usuario.id)
        .first()
    )

    if not es_propietario:
        raise HTTPException(status_code=403, detail="No tienes acceso a este curso")

    leccion = sesion.query(Leccion).filter(Leccion.id == leccion_id).first()
    if not leccion:
        raise HTTPException(status_code=404, detail="Lección no encontrada")

    # Leer contenido del archivo
    contenido = await archivo.read()

    # Crear video en Bunny
    bunny_servicio = BunnyStreamServicio()
    video_bunny = bunny_servicio.crear_video(f"{leccion.titulo} - {curso_id}")

    if not video_bunny:
        raise HTTPException(status_code=500, detail="Error al crear video en Bunny")

    # Subir archivo
    video_id = video_bunny.get("guid")
    resultado = bunny_servicio.subir_video(video_id, contenido)

    if not resultado:
        leccion.estado_video = "ERROR"
        sesion.commit()
        raise HTTPException(status_code=500, detail="Error al subir video")

    # Obtener URL de reproducción
    url_reproduccion = bunny_servicio.obtener_url_reproduccion(video_id, config.BUNNY_HOSTNAME)
    thumbnail = bunny_servicio.obtener_thumbnail(video_id, config.BUNNY_HOSTNAME)

    # Actualizar lección
    leccion.bunny_video_id = video_id
    leccion.video_url = url_reproduccion
    leccion.bunny_thumbnail_url = thumbnail
    leccion.estado_video = "PROCESANDO"
    sesion.commit()

    logger.info(f"Video subido para lección {leccion_id}: {video_id}")

    return {
        "success": True,
        "video_id": video_id,
        "thumbnail": thumbnail,
        "mensaje": "Video subido. Procesando...",
    }


@router.post("/cursos/{curso_id}/lecciones/{leccion_id}/material")
async def subir_material(
    curso_id: int,
    leccion_id: int,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
    archivo: UploadFile = File(...),
):
    """Subir material complementario"""
    from app.servicios.bunny_cdn_servicio import BunnyCDNServicio
    from app.modelos import Material

    usuario = verificar_profesor(request, sesion)

    from app.modelos import CursoInstructor

    es_propietario = (
        sesion.query(CursoInstructor)
        .filter(CursoInstructor.curso_id == curso_id, CursoInstructor.usuario_id == usuario.id)
        .first()
    )

    if not es_propietario:
        raise HTTPException(status_code=403, detail="No tienes acceso a este curso")

    leccion = sesion.query(Leccion).filter(Leccion.id == leccion_id).first()
    if not leccion:
        raise HTTPException(status_code=404, detail="Lección no encontrada")

    # Determinar tipo de archivo
    tipo = archivo.content_type or "application/octet-stream"
    if tipo.startswith("image/"):
        tipo_archivo = "IMG"
    elif tipo == "application/pdf":
        tipo_archivo = "PDF"
    elif "word" in tipo:
        tipo_archivo = "DOC"
    elif "zip" in tipo or "compressed" in tipo:
        tipo_archivo = "ZIP"
    else:
        tipo_archivo = "OTRO"

    # Leer contenido
    contenido = await archivo.read()

    # Subir a Bunny CDN
    bunny_cdn = BunnyCDNServicio()
    nombre_archivo = f"{leccion_id}_{archivo.filename}"
    resultado = bunny_cdn.subir_archivo(nombre_archivo, contenido, ruta=f"cursos/{curso_id}")

    if not resultado:
        raise HTTPException(status_code=500, error="Error al subir archivo")

    # Guardar en base de datos
    material = Material(
        leccion_id=leccion_id,
        titulo=archivo.filename,
        tipo_archivo=tipo_archivo,
        url=resultado["url"],
        tamanho_bytes=len(contenido),
        nombre_original=archivo.filename,
        usuario_subio_id=usuario.id,
    )
    sesion.add(material)
    sesion.commit()

    logger.info(f"Material subido: {archivo.filename}")
    return {"success": True, "material_id": material.id, "url": resultado["url"]}
