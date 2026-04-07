from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
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


class CrearProfesorRequest(BaseModel):
    email: str
    contrasena: str
    nombre: str
    apellido: str
    telefono: str = None
    biografia: str = None
    especialidad: str = None


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
def listar_profesores(request: Request, sesion: Session = Depends(obtener_sesion)):
    """Listar todos los profesores"""
    usuario = verificar_admin(request, sesion)

    profesores = sesion.query(Usuario).filter(Usuario.rol == RolUsuario.PROFESOR).all()

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
        ]
    }


@router.post("/profesores")
def crear_profesor(
    data: CrearProfesorRequest, request: Request, sesion: Session = Depends(obtener_sesion)
):
    """Crear un nuevo profesor"""
    usuario = verificar_admin(request, sesion)

    # Verificar que el email no existe
    existe = sesion.query(Usuario).filter(Usuario.email == data.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    # Crear profesor
    auth_servicio = AuthServicio(sesion)
    try:
        profesor = auth_servicio.registrar_usuario(
            email=data.email,
            contrasena=data.contrasena,
            nombre=data.nombre,
            apellido=data.apellido,
            rol=RolUsuario.PROFESOR,
        )

        # Actualizar campos adicionales
        profesor.telefono = data.telefono
        profesor.biografia = data.biografia
        profesor.especialidad = data.especialidad
        sesion.commit()

        logger.info(f"Profesor creado: {profesor.email}")
        return {"success": True, "profesor_id": profesor.id, "email": profesor.email}

    except Exception as e:
        logger.error(f"Error al crear profesor: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/profesores/{profesor_id}")
def eliminar_profesor(
    profesor_id: int, request: Request, sesion: Session = Depends(obtener_sesion)
):
    """Desactivar un profesor"""
    usuario = verificar_admin(request, sesion)

    profesor = (
        sesion.query(Usuario)
        .filter(Usuario.id == profesor_id, Usuario.rol == RolUsuario.PROFESOR)
        .first()
    )

    if not profesor:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")

    profesor.activo = False
    sesion.commit()

    logger.info(f"Profesor desactivado: {profesor.email}")
    return {"success": True, "message": "Profesor desactivado correctamente"}


@router.put("/profesores/{profesor_id}")
def actualizar_profesor(
    profesor_id: int,
    data: CrearProfesorRequest,
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

    # Verificar email único
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
