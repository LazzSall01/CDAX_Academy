from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.database import obtener_sesion
from app.logs import logger
from app.modelos import Usuario, RolUsuario, Curso
from app.servicios.auth_servicio import AuthServicio
from slugify import slugify

router = APIRouter(prefix="/coordinador", tags=["Coordinador"])


def verificar_coordinador(request: Request, sesion: Session = Depends(obtener_sesion)):
    """Middleware para verificar que el usuario es COORDINADOR"""
    from app.gui import obtener_usuario_desde_cookie

    usuario = obtener_usuario_desde_cookie(request, sesion)
    if not usuario or usuario.rol not in [RolUsuario.ADMIN, RolUsuario.COORDINADOR]:
        logger.warning(f"Acceso denegado a /coordinador - usuario: {usuario}")
        raise HTTPException(
            status_code=403, detail="Acceso denegado. Se requiere rol de coordinador."
        )
    return usuario


class CrearProfesorRequest(BaseModel):
    email: EmailStr = Field(..., description="Email del profesor")
    contrasena: str = Field(..., min_length=6, max_length=100, description="Contraseña")
    nombre: str = Field(..., min_length=1, max_length=100, description="Nombre")
    apellido: str = Field(..., min_length=1, max_length=100, description="Apellido")
    telefono: Optional[str] = Field(None, max_length=20, description="Teléfono")
    biografia: Optional[str] = Field(None, max_length=2000, description="Biografía")
    especialidad: Optional[str] = Field(None, max_length=200, description="Especialidad")


class CrearCursoRequest(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=255, description="Título del curso")
    descripcion: str = Field(..., max_length=2000, description="Descripción del curso")
    precio: int = Field(..., ge=0, description="Precio del curso")
    duracion_horas: Optional[int] = Field(None, ge=1, description="Duración en horas")
    modalidad: str = Field(default="EN_LINEA", description="Modalidad del curso")
    incluye_diploma: bool = Field(default=True, description="Incluye diploma")
    incluye_materiales: bool = Field(default=True, description="Incluye materiales")
    requisitos_admision: Optional[str] = Field(
        None, max_length=2000, description="Requisitos de admisión"
    )


@router.get("/dashboard")
def dashboard(request: Request, sesion: Session = Depends(obtener_sesion)):
    """Dashboard del coordinador"""
    usuario = verificar_coordinador(request, sesion)

    total_profesores = (
        sesion.query(Usuario)
        .filter(Usuario.rol == RolUsuario.PROFESOR, Usuario.activo == True)
        .count()
    )
    total_alumnos = (
        sesion.query(Usuario)
        .filter(Usuario.rol == RolUsuario.ALUMNO, Usuario.activo == True)
        .count()
    )
    total_cursos = sesion.query(Curso).count()
    cursos_activos = sesion.query(Curso).filter(Curso.activo == True).count()

    return {
        "usuario": usuario,
        "estadisticas": {
            "total_profesores": total_profesores,
            "total_alumnos": total_alumnos,
            "total_cursos": total_cursos,
            "cursos_activos": cursos_activos,
        },
    }


@router.get("/profesores")
def listar_profesores(
    request: Request,
    sesion: Session = Depends(obtener_sesion),
    pagina: int = 1,
    por_pagina: int = 20,
    buscar: str = None,
):
    """Listar todos los profesores con paginación"""
    usuario = verificar_coordinador(request, sesion)

    pagina = max(1, pagina)
    por_pagina = min(max(1, por_pagina), 100)

    query = sesion.query(Usuario).filter(Usuario.rol == RolUsuario.PROFESOR)

    if buscar:
        query = query.filter(
            (Usuario.nombre.ilike(f"%{buscar}%"))
            | (Usuario.apellido.ilike(f"%{buscar}%"))
            | (Usuario.email.ilike(f"%{buscar}%"))
        )

    total = query.count()
    profesores = (
        query.order_by(Usuario.fecha_registro.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )

    return {
        "profesores": [
            {
                "id": p.id,
                "email": p.email,
                "nombre": p.nombre,
                "apellido": p.apellido,
                "telefono": p.telefono,
                "especialidad": p.especialidad,
                "biografia": p.biografia,
                "activo": p.activo,
                "fecha_registro": p.fecha_registro.isoformat() if p.fecha_registro else None,
            }
            for p in profesores
        ],
        "paginacion": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total,
            "total_paginas": (total + por_pagina - 1) // por_pagina,
        },
    }


@router.post("/profesores")
def crear_profesor(
    data: CrearProfesorRequest, request: Request, sesion: Session = Depends(obtener_sesion)
):
    """Crear un nuevo profesor"""
    usuario = verificar_coordinador(request, sesion)

    existe = sesion.query(Usuario).filter(Usuario.email == data.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    auth_servicio = AuthServicio(sesion)
    try:
        profesor = auth_servicio.registrar_usuario(
            email=data.email,
            contrasena=data.contrasena,
            nombre=data.nombre,
            apellido=data.apellido,
            rol=RolUsuario.PROFESOR,
        )

        profesor.telefono = data.telefono
        profesor.biografia = data.biografia
        profesor.especialidad = data.especialidad
        sesion.commit()

        logger.info(f"Profesor creado por coordinador {usuario.email}: {profesor.email}")
        return {"success": True, "profesor_id": profesor.id, "email": profesor.email}

    except Exception as e:
        logger.error(f"Error al crear profesor: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/profesores/{profesor_id}")
def actualizar_profesor(
    profesor_id: int,
    data: CrearProfesorRequest,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """Actualizar un profesor"""
    usuario = verificar_coordinador(request, sesion)

    profesor = (
        sesion.query(Usuario)
        .filter(Usuario.id == profesor_id, Usuario.rol == RolUsuario.PROFESOR)
        .first()
    )

    if not profesor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")

    email_existe = (
        sesion.query(Usuario).filter(Usuario.email == data.email, Usuario.id != profesor_id).first()
    )
    if email_existe:
        raise HTTPException(status_code=400, detail="El email ya está en uso")

    profesor.email = data.email
    profesor.nombre = data.nombre
    profesor.apellido = data.apellido
    profesor.telefono = data.telefono
    profesor.biografia = data.biografia
    profesor.especialidad = data.especialidad

    if data.contrasena:
        from app.repositorios.usuario_repositorio import hash_contrasena

        profesor.contrasena_hash = hash_contrasena(data.contrasena)

    sesion.commit()

    logger.info(f"Profesor actualizado por coordinador {usuario.email}: {profesor.email}")
    return {"success": True, "profesor_id": profesor.id}


@router.delete("/profesores/{profesor_id}")
def eliminar_profesor(
    profesor_id: int, request: Request, sesion: Session = Depends(obtener_sesion)
):
    """Desactivar un profesor"""
    usuario = verificar_coordinador(request, sesion)

    profesor = (
        sesion.query(Usuario)
        .filter(Usuario.id == profesor_id, Usuario.rol == RolUsuario.PROFESOR)
        .first()
    )

    if not profesor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")

    profesor.activo = False
    sesion.commit()

    logger.info(f"Profesor desactivado por coordinador {usuario.email}: {profesor.email}")
    return {"success": True, "message": "Profesor desactivado correctamente"}


@router.get("/alumnos")
def listar_alumnos(
    request: Request,
    sesion: Session = Depends(obtener_sesion),
    pagina: int = 1,
    por_pagina: int = 20,
    buscar: str = None,
):
    """Listar todos los alumnos con paginación"""
    usuario = verificar_coordinador(request, sesion)

    pagina = max(1, pagina)
    por_pagina = min(max(1, por_pagina), 100)

    from app.modelos import Suscripcion

    query = sesion.query(Usuario).filter(Usuario.rol == RolUsuario.ALUMNO)

    if buscar:
        query = query.filter(
            (Usuario.nombre.ilike(f"%{buscar}%"))
            | (Usuario.apellido.ilike(f"%{buscar}%"))
            | (Usuario.email.ilike(f"%{buscar}%"))
        )

    total = query.count()
    alumnos = (
        query.order_by(Usuario.fecha_registro.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )

    usuario_ids = [a.id for a in alumnos]

    suscripciones_por_usuario = {}
    if usuario_ids:
        suscripciones_query = (
            sesion.query(Suscripcion.usuario_id, func.count(Suscripcion.id))
            .filter(Suscripcion.usuario_id.in_(usuario_ids), Suscripcion.estado == "ACTIVO")
            .group_by(Suscripcion.usuario_id)
            .all()
        )
        for sc in suscripciones_query:
            suscripciones_por_usuario[sc[0]] = sc[1]

    resultado = []
    for a in alumnos:
        resultado.append(
            {
                "id": a.id,
                "email": a.email,
                "nombre": a.nombre,
                "apellido": a.apellido,
                "activo": a.activo,
                "cursos_inscritos": suscripciones_por_usuario.get(a.id, 0),
                "fecha_registro": a.fecha_registro.isoformat() if a.fecha_registro else None,
            }
        )

    return {
        "alumnos": resultado,
        "paginacion": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total,
            "total_paginas": (total + por_pagina - 1) // por_pagina,
        },
    }


@router.put("/alumnos/{alumno_id}")
def actualizar_alumno(
    alumno_id: int,
    nombre: str,
    apellido: str,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """Actualizar un alumno"""
    usuario = verificar_coordinador(request, sesion)

    alumno = (
        sesion.query(Usuario)
        .filter(Usuario.id == alumno_id, Usuario.rol == RolUsuario.ALUMNO)
        .first()
    )

    if not alumno:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    alumno.nombre = nombre
    alumno.apellido = apellido
    sesion.commit()

    logger.info(f"Alumno actualizado por coordinador {usuario.email}: {alumno.email}")
    return {"success": True, "alumno_id": alumno.id}


@router.delete("/alumnos/{alumno_id}")
def eliminar_alumno(alumno_id: int, request: Request, sesion: Session = Depends(obtener_sesion)):
    """Desactivar un alumno"""
    usuario = verificar_coordinador(request, sesion)

    alumno = (
        sesion.query(Usuario)
        .filter(Usuario.id == alumno_id, Usuario.rol == RolUsuario.ALUMNO)
        .first()
    )

    if not alumno:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    alumno.activo = False
    sesion.commit()

    logger.info(f"Alumno desactivado por coordinador {usuario.email}: {alumno.email}")
    return {"success": True, "message": "Alumno desactivado correctamente"}


@router.get("/cursos")
def listar_cursos(
    request: Request,
    sesion: Session = Depends(obtener_sesion),
    pagina: int = 1,
    por_pagina: int = 20,
    buscar: str = None,
):
    """Listar todos los cursos con paginación"""
    usuario = verificar_coordinador(request, sesion)

    pagina = max(1, pagina)
    por_pagina = min(max(1, por_pagina), 100)

    from app.modelos import Modulo, Leccion, Suscripcion

    query = sesion.query(Curso)

    if buscar:
        query = query.filter(Curso.titulo.ilike(f"%{buscar}%"))

    total = query.count()
    cursos = (
        query.order_by(Curso.fecha_creacion.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )

    curso_ids = [c.id for c in cursos]

    modulos_por_curso = {}
    modulos_query = (
        sesion.query(Modulo.curso_id, func.count(Modulo.id))
        .filter(Modulo.curso_id.in_(curso_ids))
        .group_by(Modulo.curso_id)
        .all()
    )
    for mc in modulos_query:
        modulos_por_curso[mc[0]] = mc[1]

    lecciones_por_curso = {}
    if curso_ids:
        lecciones_query = (
            sesion.query(Modulo.curso_id, func.count(Leccion.id))
            .join(Leccion)
            .filter(Modulo.curso_id.in_(curso_ids))
            .group_by(Modulo.curso_id)
            .all()
        )
        for lc in lecciones_query:
            lecciones_por_curso[lc[0]] = lc[1]

    alumnos_por_curso = {}
    if curso_ids:
        alumnos_query = (
            sesion.query(Suscripcion.curso_id, func.count(Suscripcion.id))
            .filter(Suscripcion.curso_id.in_(curso_ids), Suscripcion.estado == "ACTIVO")
            .group_by(Suscripcion.curso_id)
            .all()
        )
        for ac in alumnos_query:
            alumnos_por_curso[ac[0]] = ac[1]

    resultado = []
    for c in cursos:
        resultado.append(
            {
                "id": c.id,
                "titulo": c.titulo,
                "slug": c.slug,
                "tipo_programa": c.tipo_programa,
                "precio": c.precio,
                "activo": c.activo,
                "modulos": modulos_por_curso.get(c.id, 0),
                "lecciones": lecciones_por_curso.get(c.id, 0),
                "alumnos": alumnos_por_curso.get(c.id, 0),
                "fecha_creacion": c.fecha_creacion.isoformat() if c.fecha_creacion else None,
            }
        )

    return {
        "cursos": resultado,
        "paginacion": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total,
            "total_paginas": (total + por_pagina - 1) // por_pagina,
        },
    }


@router.post("/cursos")
def crear_curso(
    data: CrearCursoRequest, request: Request, sesion: Session = Depends(obtener_sesion)
):
    """Crear un nuevo curso"""
    usuario = verificar_coordinador(request, sesion)

    slug = slugify(data.titulo)
    existente = sesion.query(Curso).filter(Curso.slug == slug).first()
    if existente:
        slug = f"{slug}-{usuario.id}"

    curso = Curso(
        titulo=data.titulo,
        slug=slug,
        descripcion=data.descripcion,
        precio=data.precio,
        tipo_programa="CURSO",
        duracion_horas=data.duracion_horas,
        modalidad=data.modalidad,
        incluye_diploma=data.incluye_diploma,
        incluye_materiales=data.incluye_materiales,
        requisitos_admision=data.requisitos_admision,
        estado_inscripcion="PROXIMAMENTE",
        activo=True,
    )
    sesion.add(curso)
    sesion.commit()

    logger.info(f"Curso creado por coordinador {usuario.email}: {curso.titulo}")
    return {"success": True, "curso_id": curso.id, "slug": curso.slug}


@router.put("/cursos/{curso_id}")
def actualizar_curso(
    curso_id: int,
    titulo: str = None,
    descripcion: str = None,
    precio: int = None,
    activo: bool = None,
    request: Request = None,
    sesion: Session = Depends(obtener_sesion),
):
    """Actualizar un curso"""
    from app.gui import obtener_usuario_desde_cookie

    usuario = verificar_coordinador(request, sesion)

    curso = sesion.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    if titulo:
        curso.titulo = titulo
    if descripcion:
        curso.descripcion = descripcion
    if precio is not None:
        curso.precio = precio
    if activo is not None:
        curso.activo = activo

    sesion.commit()

    logger.info(f"Curso actualizado por coordinador {usuario.email}: {curso.titulo}")
    return {"success": True, "curso_id": curso.id}


# ==================== CURSOS - EDITAR ====================
class ActualizarCursoCoordinadorRequest(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=255)
    descripcion: Optional[str] = Field(None, max_length=2000)
    descripcion_larga: Optional[str] = None
    modalidad: Optional[str] = None
    duracion_horas: Optional[int] = None
    capacidad_maxima: Optional[int] = None
    precio: Optional[int] = Field(None, ge=0)


@router.get("/cursos/{curso_id}")
def obtener_curso_coordinador(curso_id: int, sesion: Session = Depends(obtener_sesion)):
    """Obtener un curso para editar"""
    from app.modelos import Curso, Modulo, Leccion

    curso = sesion.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    modulos = sesion.query(Modulo).filter(Modulo.curso_id == curso_id).order_by(Modulo.orden).all()
    modulos_data = []
    for m in modulos:
        lecciones = (
            sesion.query(Leccion).filter(Leccion.modulo_id == m.id).order_by(Leccion.orden).all()
        )
        modulos_data.append(
            {
                "id": m.id,
                "titulo": m.titulo,
                "orden": m.orden,
                "lecciones": [
                    {
                        "id": l.id,
                        "titulo": l.titulo,
                        "orden": l.orden,
                        "video_url": l.video_url,
                        "bunny_video_id": l.bunny_video_id,
                        "estado_video": l.estado_video,
                    }
                    for l in lecciones
                ],
            }
        )
    return {
        "id": curso.id,
        "titulo": curso.titulo,
        "slug": curso.slug,
        "descripcion": curso.descripcion,
        "descripcion_larga": curso.descripcion_larga,
        "precio": curso.precio,
        "tipo_programa": curso.tipo_programa,
        "activo": curso.activo,
        "modalidad": curso.modalidad,
        "duracion_horas": curso.duracion_horas,
        "capacidad_maxima": curso.capacidad_maxima,
        "modulos": modulos_data,
    }


@router.put("/cursos/{curso_id}")
def actualizar_curso_coordinador_completo(
    curso_id: int,
    datos: ActualizarCursoCoordinadorRequest,
    sesion: Session = Depends(obtener_sesion),
):
    """Actualizar un curso - precio queda pendiente de aprobación"""
    from app.modelos import Curso

    usuario = verificar_coordinador(None, sesion)
    curso = sesion.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    datos_dict = datos.model_dump(exclude_none=True)

    for campo, valor in datos_dict.items():
        if valor is not None:
            if campo == "precio":
                curso.precio_pendiente = valor
                curso.estado_aprobacion = "PENDIENTE"
                logger.info(
                    f"Coordinador {usuario.email} cambió precio a {valor} - pendiente aprobación"
                )
            else:
                setattr(curso, campo, valor)
    sesion.commit()
    logger.info(f"Curso actualizado por coordinador: {curso_id}")
    return {
        "success": True,
        "estado_aprobacion": "PENDIENTE",
        "mensaje": "Precio pendiente de aprobación por admin",
    }
