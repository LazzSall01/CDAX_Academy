from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.database import obtener_sesion
from app.logs import logger
from app.modelos import Usuario, RolUsuario
from app.servicios.auth_servicio import AuthServicio

router = APIRouter(prefix="/admin", tags=["Admin"])


def verificar_admin(request: Request, sesion: Session = Depends(obtener_sesion)):
    """Middleware para verificar que el usuario es ADMIN"""
    from app.gui import obtener_usuario_desde_cookie

    usuario = obtener_usuario_desde_cookie(request, sesion)
    if not usuario or usuario.rol != RolUsuario.ADMIN:
        logger.warning(f"Acceso denegado a /admin - usuario: {usuario}")
        raise HTTPException(
            status_code=403, detail="Acceso denegado. Se requiere rol de administrador."
        )
    return usuario


class CrearUsuarioRequest(BaseModel):
    email: EmailStr = Field(..., description="Email del usuario")
    contrasena: str = Field(..., min_length=6, max_length=100, description="Contraseña")
    contrasena_confirmar: Optional[str] = Field(
        None, description="Confirmar contraseña (para validación)"
    )
    nombre: str = Field(..., min_length=1, max_length=100, description="Nombre")
    apellido: str = Field(..., min_length=1, max_length=100, description="Apellido")
    usuario: Optional[str] = Field(
        None, max_length=100, description="Nombre de usuario para acceder"
    )
    rol: str = Field(..., description="Rol del usuario: PROFESOR, COORDINADOR")
    telefono: Optional[str] = Field(None, max_length=20, description="Teléfono")
    biografia: Optional[str] = Field(None, max_length=2000, description="Biografía")
    especialidad: Optional[str] = Field(None, max_length=200, description="Especialidad")


@router.get("/dashboard")
def dashboard(request: Request, sesion: Session = Depends(obtener_sesion)):
    """Dashboard del administrador"""
    usuario = verificar_admin(request, sesion)

    # Estadísticas
    total_usuarios = sesion.query(Usuario).count()
    total_profesores = sesion.query(Usuario).filter(Usuario.rol == RolUsuario.PROFESOR).count()
    total_alumnos = sesion.query(Usuario).filter(Usuario.rol == RolUsuario.ALUMNO).count()

    from app.modelos import Curso

    total_cursos = sesion.query(Curso).count()

    return {
        "usuario": usuario,
        "estadisticas": {
            "total_usuarios": total_usuarios,
            "total_profesores": total_profesores,
            "total_alumnos": total_alumnos,
            "total_cursos": total_cursos,
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
    """Listar todo el personal (profesores y coordinadores) con paginación"""
    usuario = verificar_admin(request, sesion)

    pagina = max(1, pagina)
    por_pagina = min(max(1, por_pagina), 100)

    query = sesion.query(Usuario).filter(
        Usuario.rol.in_([RolUsuario.PROFESOR, RolUsuario.COORDINADOR])
    )

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
                "rol": p.rol.value,
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


@router.get("/usuarios/{usuario_id}")
def obtener_usuario(usuario_id: int, request: Request, sesion: Session = Depends(obtener_sesion)):
    """Obtener un usuario específico"""
    verificar_admin(request, sesion)

    usuario = sesion.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "apellido": usuario.apellido,
        "email": usuario.email,
        "telefono": usuario.telefono,
        "rol": usuario.rol.value,
        "activo": usuario.activo,
    }


@router.put("/usuarios/{usuario_id}")
def actualizar_usuario(
    usuario_id: int,
    nombre: Optional[str] = None,
    apellido: Optional[str] = None,
    email: Optional[EmailStr] = None,
    contrasena: Optional[str] = None,
    telefono: Optional[str] = None,
    request: Request = None,
    sesion: Session = Depends(obtener_sesion),
):
    """Actualizar un usuario"""
    verificar_admin(request, sesion)

    usuario = sesion.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if nombre:
        usuario.nombre = nombre
    if apellido:
        usuario.apellido = apellido
    if email:
        # Verificar que el email no esté en uso
        existe = (
            sesion.query(Usuario).filter(Usuario.email == email, Usuario.id != usuario_id).first()
        )
        if existe:
            raise HTTPException(status_code=400, detail="El email ya está en uso")
        usuario.email = email
    if contrasena:
        from app.repositorios.usuario_repositorio import hash_contrasena

        usuario.contrasena_hash = hash_contrasena(contrasena)
    if telefono is not None:
        usuario.telefono = telefono

    sesion.commit()
    logger.info(f"Usuario actualizado: {usuario.email}")
    return {"success": True}


@router.post("/usuarios")
def crear_usuario(
    data: CrearUsuarioRequest, request: Request, sesion: Session = Depends(obtener_sesion)
):
    """Crear un nuevo usuario con rol específico (PROFESOR o COORDINADOR)"""
    usuario = verificar_admin(request, sesion)

    rol_valido = data.rol.upper()
    if rol_valido not in ["PROFESOR", "COORDINADOR", "ALUMNO"]:
        raise HTTPException(
            status_code=400, detail="Rol no válido. Use PROFESOR, COORDINADOR o ALUMNO"
        )

    rol = RolUsuario[rol_valido]

    existe = sesion.query(Usuario).filter(Usuario.email == data.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    # Verificar si el usuario ya existe
    if data.usuario:
        existe_usuario = sesion.query(Usuario).filter(Usuario.usuario == data.usuario).first()
        if existe_usuario:
            raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado")

    auth_servicio = AuthServicio(sesion)
    try:
        nuevo_usuario = auth_servicio.registrar_usuario(
            email=data.email,
            contrasena=data.contrasena,
            nombre=data.nombre,
            apellido=data.apellido,
            rol=rol,
            usuario_nombre=data.usuario,
        )

        nuevo_usuario.telefono = data.telefono
        nuevo_usuario.biografia = data.biografia
        nuevo_usuario.especialidad = data.especialidad
        sesion.commit()

        logger.info(f"Usuario creado con rol {rol.value}: {nuevo_usuario.email}")
        return {
            "success": True,
            "usuario_id": nuevo_usuario.id,
            "email": nuevo_usuario.email,
            "rol": rol.value,
        }

    except Exception as e:
        logger.error(f"Error al crear usuario: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/profesores/{profesor_id}")
def eliminar_profesor(
    profesor_id: int, request: Request, sesion: Session = Depends(obtener_sesion)
):
    """Desactivar un usuario (profesor o coordinador)"""
    verificar_admin(request, sesion)

    usuario = sesion.query(Usuario).filter(Usuario.id == profesor_id).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # No permitir eliminar al admin
    if usuario.rol == RolUsuario.ADMIN:
        raise HTTPException(status_code=400, detail="No puedes eliminar al administrador")

    usuario.activo = False
    sesion.commit()

    logger.info(f"Usuario desactivado: {usuario.email}")
    return {"success": True, "message": "Usuario desactivado correctamente"}


@router.put("/profesores/{profesor_id}")
def actualizar_profesor(
    profesor_id: int,
    data: CrearUsuarioRequest,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """Actualizar un profesor"""
    usuario = verificar_admin(request, sesion)

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

    logger.info(f"Profesor actualizado: {profesor.email}")
    return {"success": True, "profesor_id": profesor.id}


@router.get("/configuracion/bunny")
def obtener_config_bunny(request: Request, sesion: Session = Depends(obtener_sesion)):
    """Obtener configuración de Bunny"""
    usuario = verificar_admin(request, sesion)

    from app.modelos import ConfiguracionBunny

    config = sesion.query(ConfiguracionBunny).first()

    if config:
        return {
            "api_key": config.api_key[:10] + "..." if config.api_key else None,
            "library_id": config.library_id,
            "hostname": config.hostname,
            "storage_zone": config.storage_zone,
            "activo": config.activo,
        }
    return {}


@router.post("/configuracion/bunny")
def guardar_config_bunny(
    api_key: str,
    library_id: str,
    hostname: str,
    storage_zone: str = None,
    request: Request = None,
    sesion: Session = Depends(obtener_sesion),
):
    """Guardar configuración de Bunny"""
    from app.modelos import ConfiguracionBunny

    config_existente = sesion.query(ConfiguracionBunny).first()

    if config_existente:
        config_existente.api_key = api_key
        config_existente.library_id = library_id
        config_existente.hostname = hostname
        config_existente.storage_zone = storage_zone
    else:
        config = ConfiguracionBunny(
            api_key=api_key,
            library_id=library_id,
            hostname=hostname,
            storage_zone=storage_zone,
            activo=True,
        )
        sesion.add(config)

    sesion.commit()
    logger.info("Configuración de Bunny guardada")
    return {"success": True}


# ==================== GESTIÓN DE CURSOS ====================
class CrearCursoRequest(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=255)
    descripcion: Optional[str] = Field(None, max_length=2000)
    precio: int = Field(0, ge=0)
    tipo_programa: str = Field("CURSO")


class ActualizarCursoRequest(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=255)
    descripcion: Optional[str] = Field(None, max_length=2000)
    descripcion_larga: Optional[str] = Field(None)
    precio: Optional[int] = Field(None, ge=0)
    tipo_programa: Optional[str] = None
    activo: Optional[bool] = None
    imagen_url: Optional[str] = Field(None, max_length=500)
    fecha_inicio: Optional[str] = None
    fecha_fin_inscripcion: Optional[str] = None
    estado_inscripcion: Optional[str] = None
    whatsapp_contacto: Optional[str] = Field(None, max_length=20)
    duracion_horas: Optional[int] = None
    modalidad: Optional[str] = None
    incluye_diploma: Optional[bool] = None
    incluye_materiales: Optional[bool] = None
    requisitos_admision: Optional[str] = None
    capacidad_maxima: Optional[int] = None


@router.get("/cursos")
def listar_cursos(sesion: Session = Depends(obtener_sesion)):
    """Listar todos los cursos para admin"""
    from app.modelos import Curso, Modulo, Leccion

    cursos_orm = sesion.query(Curso).all()
    resultado = []
    for c in cursos_orm:
        modulos_count = sesion.query(Modulo).filter(Modulo.curso_id == c.id).count()
        lecciones_count = sesion.query(Leccion).join(Modulo).filter(Modulo.curso_id == c.id).count()
        resultado.append(
            {
                "id": c.id,
                "titulo": c.titulo,
                "slug": c.slug,
                "descripcion": c.descripcion,
                "precio": c.precio,
                "tipo_programa": c.tipo_programa,
                "activo": c.activo,
                "imagen_url": c.imagen_url,
                "modulos": modulos_count,
                "lecciones": lecciones_count,
            }
        )
    return resultado


@router.post("/cursos")
def crear_curso(datos: CrearCursoRequest, sesion: Session = Depends(obtener_sesion)):
    """Crear un nuevo curso"""
    from app.modelos import Curso
    import slugify

    titre_slug = slugify.slugify(datos.titulo)
    curso = Curso(
        titulo=datos.titulo,
        slug=titre_slug,
        descripcion=datos.descripcion,
        precio=datos.precio,
        tipo_programa=datos.tipo_programa,
        activo=True,
    )
    sesion.add(curso)
    sesion.commit()
    sesion.refresh(curso)
    logger.info(f"Curso creado: {curso.id} - {curso.titulo}")
    return {"id": curso.id, "titulo": curso.titulo}


@router.get("/cursos/{curso_id}")
def obtener_curso(curso_id: int, sesion: Session = Depends(obtener_sesion)):
    """Obtener un curso específico"""
    from app.modelos import Curso, Modulo, Leccion, Usuario, CursoInstructor

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
                    {"id": l.id, "titulo": l.titulo, "orden": l.orden, "video_url": l.video_url}
                    for l in lecciones
                ],
            }
        )
    from app.modelos import Instructor

    instructores_curso = (
        sesion.query(CursoInstructor).filter(CursoInstructor.curso_id == curso_id).all()
    )
    instructores_data = []
    for ci in instructores_curso:
        inst = sesion.query(Instructor).filter(Instructor.id == ci.instructor_id).first()
        if inst:
            instructores_data.append({"id": inst.id, "nombre": f"{inst.nombre} {inst.apellido}"})
    return {
        "id": curso.id,
        "titulo": curso.titulo,
        "slug": curso.slug,
        "descripcion": curso.descripcion,
        "descripcion_larga": curso.descripcion_larga,
        "precio": curso.precio,
        "tipo_programa": curso.tipo_programa,
        "activo": curso.activo,
        "imagen_url": curso.imagen_url,
        "fecha_inicio": curso.fecha_inicio.isoformat() if curso.fecha_inicio else None,
        "fecha_fin_inscripcion": curso.fecha_fin_inscripcion.isoformat()
        if curso.fecha_fin_inscripcion
        else None,
        "estado_inscripcion": curso.estado_inscripcion,
        "whatsapp_contacto": curso.whatsapp_contacto,
        "duracion_horas": curso.duracion_horas,
        "modalidad": curso.modalidad,
        "incluye_diploma": curso.incluye_diploma,
        "incluye_materiales": curso.incluye_materiales,
        "requisitos_admision": curso.requisitos_admision,
        "capacidad_maxima": curso.capacidad_maxima,
        "modulos": modulos_data,
        "instructores": instructores_data,
    }


@router.put("/cursos/{curso_id}")
def actualizar_curso(
    curso_id: int, datos: ActualizarCursoRequest, sesion: Session = Depends(obtener_sesion)
):
    """Actualizar un curso"""
    from app.modelos import Curso
    from datetime import datetime

    curso = sesion.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    datos_dict = datos.model_dump(exclude_none=True)
    for campo, valor in datos_dict.items():
        if valor is not None:
            setattr(curso, campo, valor)
    sesion.commit()
    logger.info(f"Curso actualizado: {curso_id}")
    return {"success": True}


@router.post("/cursos/{curso_id}/toggle")
def toggle_curso(curso_id: int, sesion: Session = Depends(obtener_sesion)):
    """Activar/desactivar un curso"""
    from app.modelos import Curso

    curso = sesion.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    curso.activo = not curso.activo
    sesion.commit()
    logger.info(f"Curso toggle: {curso_id} - activo: {curso.activo}")
    return {"activo": curso.activo}


@router.delete("/cursos/{curso_id}")
def eliminar_curso(curso_id: int, sesion: Session = Depends(obtener_sesion)):
    """Eliminar un curso"""
    from app.modelos import Curso

    curso = sesion.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    sesion.delete(curso)
    sesion.commit()
    logger.info(f"Curso eliminado: {curso_id}")
    return {"success": True}


@router.post("/cursos/{curso_id}/aprobar")
def aprobar_cambio_precio(curso_id: int, sesion: Session = Depends(obtener_sesion)):
    """Aprobar cambio de precio pendiente"""
    from app.modelos import Curso

    curso = sesion.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    if curso.precio_pendiente:
        curso.precio = curso.precio_pendiente
        curso.precio_pendiente = None
        curso.estado_aprobacion = "APROBADO"
        sesion.commit()
        logger.info(f"Precio aprobado para curso {curso_id}: {curso.precio}")
        return {"success": True, "precio": curso.precio, "estado_aprobacion": "APROBADO"}

    return {"success": True, "mensaje": "No hay cambios pendientes"}


@router.post("/cursos/{curso_id}/rechazar")
def rechazar_cambio_precio(curso_id: int, sesion: Session = Depends(obtener_sesion)):
    """Rechazar cambio de precio pendiente"""
    from app.modelos import Curso

    curso = sesion.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    curso.precio_pendiente = None
    curso.estado_aprobacion = "RECHAZADO"
    sesion.commit()
    logger.info(f"Precio rechazado para curso {curso_id}")
    return {"success": True, "estado_aprobacion": "RECHAZADO"}


@router.post("/cursos/{curso_id}/asignar-instructor")
def asignar_instructor(
    curso_id: int,
    datos: dict,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """Asignar un instructor a un curso"""
    from app.modelos import Curso, Instructor, CursoInstructor, Usuario, RolUsuario

    verificar_admin(request, sesion)

    usuario_id = datos.get("instructor_id")
    if not usuario_id:
        raise HTTPException(status_code=400, detail="Se requiere instructor_id")

    # Verificar que el usuario existe y es PROFESOR
    usuario = (
        sesion.query(Usuario)
        .filter(Usuario.id == usuario_id, Usuario.rol == RolUsuario.PROFESOR)
        .first()
    )
    if not usuario:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")

    # Verificar que el curso existe
    curso = sesion.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # Verificar si ya está instructor creado, si no crearlo
    instructor = sesion.query(Instructor).filter(Instructor.email == usuario.email).first()
    if not instructor:
        instructor = Instructor(
            nombre=usuario.nombre, apellido=usuario.apellido, email=usuario.email, activo=True
        )
        sesion.add(instructor)
        sesion.flush()
        logger.info(f"Instructor creado desde usuario {usuario_id}")

    # Verificar si ya está asignado
    existe = (
        sesion.query(CursoInstructor)
        .filter(
            CursoInstructor.curso_id == curso_id, CursoInstructor.instructor_id == instructor.id
        )
        .first()
    )
    if existe:
        raise HTTPException(status_code=400, detail="El instructor ya está asignado")

    # Crear la relación
    rel = CursoInstructor(curso_id=curso_id, instructor_id=instructor.id)
    sesion.add(rel)
    sesion.commit()

    logger.info(f"Instructor {instructor.id} asignado al curso {curso_id}")
    return {"success": True}


@router.post("/cursos/{curso_id}/remover-instructor")
def remover_instructor(
    curso_id: int,
    datos: dict,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """Remover un instructor de un curso"""
    from app.modelos import Instructor, Usuario, RolUsuario

    verificar_admin(request, sesion)

    usuario_id = datos.get("instructor_id")
    if not usuario_id:
        raise HTTPException(status_code=400, detail="Se requiere instructor_id")

    # Obtener el email del instructor
    usuario = sesion.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Buscar instructor en tabla instructores
    instructor = sesion.query(Instructor).filter(Instructor.email == usuario.email).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor no encontrado")

    # Buscar y eliminar la relación
    from app.modelos import CursoInstructor

    rel = (
        sesion.query(CursoInstructor)
        .filter(
            CursoInstructor.curso_id == curso_id, CursoInstructor.instructor_id == instructor.id
        )
        .first()
    )

    if not rel:
        raise HTTPException(status_code=404, detail="Instructor no asignado a este curso")

    sesion.delete(rel)
    sesion.commit()

    logger.info(f"Instructor {instructor.id} removido del curso {curso_id}")
    return {"success": True}


# ==================== GESTIÓN DE ALUMNOS ====================
@router.get("/alumnos/{alumno_id}")
def obtener_alumno(alumno_id: int, request: Request, sesion: Session = Depends(obtener_sesion)):
    """Obtener un alumno específico"""
    verificar_admin(request, sesion)

    from app.modelos import Suscripcion

    alumno = sesion.query(Usuario).filter(Usuario.id == alumno_id).first()
    if not alumno:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    cursos_count = (
        sesion.query(Suscripcion)
        .filter(Suscripcion.usuario_id == alumno_id, Suscripcion.estado == "ACTIVO")
        .count()
    )

    return {
        "id": alumno.id,
        "nombre": alumno.nombre,
        "apellido": aluno.apellido,
        "email": alumno.email,
        "telefono": alumno.telefono,
        "activo": alumno.activo,
        "cursos": cursos_count,
    }


@router.put("/alumnos/{alumno_id}")
def actualizar_alumno(
    alumno_id: int,
    nombre: Optional[str] = None,
    apellido: Optional[str] = None,
    email: Optional[EmailStr] = None,
    telefono: Optional[str] = None,
    request: Request = None,
    sesion: Session = Depends(obtener_sesion),
):
    """Actualizar un aluno"""
    verificar_admin(request, sesion)

    from app.modelos import Suscripcion

    # Verificar que existe
    if sesion.query(Usuario).filter(Usuario.id == alumno_id).count() == 0:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    # Build update query dynamically
    update_fields = {}
    if nombre:
        update_fields["nombre"] = nombre
    if apellido:
        update_fields["apellido"] = apellido
    if email:
        existe = (
            sesion.query(Usuario).filter(Usuario.email == email, Usuario.id != alumno_id).first()
        )
        if existe:
            raise HTTPException(status_code=400, detail="El email ya está en uso")
        update_fields["email"] = email
    if telefono is not None:
        update_fields["telefono"] = telefono

    if update_fields:
        sesion.query(Usuario).filter(Usuario.id == alumno_id).update(update_fields)
        sesion.commit()

    logger.info(f"Alumno actualizado: {alumno_id}")
    return {"success": True}


@router.delete("/alumnos/{alumno_id}")
def eliminar_alumno(alumno_id: int, request: Request, sesion: Session = Depends(obtener_sesion)):
    """Eliminar un aluno y sus suscripciones"""
    verificar_admin(request, sesion)

    from app.modelos import Suscripcion, Progreso

    # Obtener alumno
    alumno = sesion.query(Usuario).filter(Usuario.id == alumno_id).first()
    if not alumno:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    # Eliminar suscripciones
    suscripciones = sesion.query(Suscripcion).filter(Suscripcion.usuario_id == alumno_id).all()
    for s in suscripciones:
        # Eliminar progresos
        sesion.query(Progreso).filter(Progreso.suscripcion_id == s.id).delete()
        sesion.delete(s)

    # Eliminar progreso general
    sesion.query(Progreso).filter(Progreso.usuario_id == alumno_id).delete()

    # Eliminar usuario
    sesion.delete(alumno)
    sesion.commit()

    logger.info(f"Alumno eliminado: {alumno_id}")
    return {"success": True}


@router.get("/alumnos/{alumno_id}/suscripciones")
def obtener_suscripciones_alumno(
    alumno_id: int, request: Request, sesion: Session = Depends(obtener_sesion)
):
    """Obtener suscripciones de un alumno"""
    verificar_admin(request, sesion)

    from app.modelos import Suscripcion, Curso

    suscripciones = (
        sesion.query(Suscripcion, Curso)
        .join(Curso, Suscripcion.curso_id == Curso.id)
        .filter(Suscripcion.usuario_id == alumno_id)
        .all()
    )

    resultado = []
    for s, c in suscripciones:
        resultado.append(
            {
                "id": s.id,
                "curso": c.titulo,
                "estado": s.estado,
                "fecha_inicio": s.fecha_inicio.isoformat() if s.fecha_inicio else None,
                "fecha_fin": s.fecha_fin.isoformat() if s.fecha_fin else None,
            }
        )

    return {"suscripciones": resultado}


@router.delete("/suscripciones/{suscripcion_id}")
def eliminar_suscripcion(
    suscripcion_id: int, request: Request, sesion: Session = Depends(obtener_sesion)
):
    """Eliminar una suscripción"""
    verificar_admin(request, sesion)

    from app.modelos import Suscripcion, Progreso

    suscripcion = sesion.query(Suscripcion).filter(Suscripcion.id == suscripcion_id).first()
    if not suscripcion:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada")

    # Eliminar progresos asociados
    sesion.query(Progreso).filter(Progreso.suscripcion_id == suscripcion_id).delete()

    # Eliminar suscripción
    sesion.delete(suscripcion)
    sesion.commit()

    logger.info(f"Suscripción eliminada: {suscripcion_id}")
    return {"success": True}


# ==================== MÓDULOS Y LECCIONES ====================
class CrearModuloRequest(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=255)
    orden: int = Field(..., ge=0)


class CrearLeccionRequest(BaseModel):
    modulo_id: int = Field(...)
    titulo: str = Field(..., min_length=1, max_length=255)
    descripcion: Optional[str] = None
    duracion_minutos: int = Field(default=0)
    orden: int = Field(..., ge=0)


@router.post("/cursos/{curso_id}/modulos")
def crear_modulo(
    curso_id: int,
    data: CrearModuloRequest,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """Crear un módulo"""
    from app.modelos import Modulo

    verificar_admin(request, sesion)

    modulo = Modulo(
        curso_id=curso_id,
        titulo=data.titulo,
        orden=data.orden,
    )
    sesion.add(modulo)
    sesion.commit()
    logger.info(f"Módulo creado por admin: {data.titulo}")
    return {"success": True, "modulo_id": modulo.id}


@router.post("/cursos/{curso_id}/lecciones")
def crear_leccion(
    curso_id: int,
    data: CrearLeccionRequest,
    request: Request,
    sesion: Session = Depends(obtener_sesion),
):
    """Crear una lección"""
    from app.modelos import Leccion

    verificar_admin(request, sesion)

    leccion = Leccion(
        modulo_id=data.modulo_id,
        titulo=data.titulo,
        descripcion=data.descripcion,
        duracion_minutos=data.duracion_minutos,
        orden=data.orden,
    )
    sesion.add(leccion)
    sesion.commit()
    logger.info(f"Lección creada por admin: {data.titulo}")
    return {"success": True, "leccion_id": leccion.id}
