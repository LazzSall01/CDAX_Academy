from sqlalchemy.orm import Session
from app.modelos import Usuario, RolUsuario
from app.logs import logger
from typing import Optional
import bcrypt


def hash_contrasena(contrasena: str) -> str:
    return bcrypt.hashpw(contrasena.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_contrasena_hash(contrasena: str, hash_bd: str) -> bool:
    return bcrypt.checkpw(contrasena.encode("utf-8"), hash_bd.encode("utf-8"))


class UsuarioRepositorio:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def buscar_por_email(self, email: str) -> Optional[Usuario]:
        logger.info(f"Buscando usuario por email: {email}")
        return self.sesion.query(Usuario).filter(Usuario.email == email).first()

    def buscar_por_usuario(self, nombre_usuario: str) -> Optional[Usuario]:
        logger.info(f"Buscando usuario por nombre de usuario: {nombre_usuario}")
        return self.sesion.query(Usuario).filter(Usuario.usuario == nombre_usuario).first()

    def buscar_por_google_id(self, google_id: str) -> Optional[Usuario]:
        logger.info(f"Buscando usuario por Google ID: {google_id}")
        return self.sesion.query(Usuario).filter(Usuario.google_id == google_id).first()

    def buscar_por_id(self, usuario_id: int) -> Optional[Usuario]:
        logger.info(f"Buscando usuario por ID: {usuario_id}")
        return self.sesion.query(Usuario).filter(Usuario.id == usuario_id).first()

    def crear_usuario_google(
        self,
        google_id: str,
        email: str,
        nombre: str,
        apellido: str,
        avatar_url: Optional[str] = None,
    ) -> Usuario:
        logger.info(f"Creando nuevo usuario Google: {email}")
        usuario = Usuario(
            google_id=google_id,
            email=email,
            nombre=nombre,
            apellido=apellido,
            avatar_url=avatar_url,
            rol=RolUsuario.ALUMNO,
        )
        self.sesion.add(usuario)
        self.sesion.commit()
        self.sesion.refresh(usuario)
        logger.info(f"Usuario creado exitosamente con ID: {usuario.id}")
        return usuario

    def crear_usuario_email(
        self,
        email: str,
        contrasena: str,
        nombre: str,
        apellido: str,
        rol: RolUsuario = None,
        usuario: str = None,
    ) -> Usuario:
        logger.info(f"Creando nuevo usuario con usuario: {usuario or email}")
        contrasena_hash = hash_contrasena(contrasena)
        if rol is None:
            rol = RolUsuario.ALUMNO
        usuario_obj = Usuario(
            email=email,
            contrasena_hash=contrasena_hash,
            nombre=nombre,
            apellido=apellido,
            rol=rol,
            usuario=usuario,
        )
        self.sesion.add(usuario_obj)
        self.sesion.commit()
        self.sesion.refresh(usuario_obj)
        logger.info(f"Usuario creado exitosamente con ID: {usuario_obj.id}, rol: {rol.value}")
        return usuario_obj

    def verificar_contrasena(self, usuario: Usuario, contrasena: str) -> bool:
        if not usuario.contrasena_hash:
            return False
        return verificar_contrasena_hash(contrasena, usuario.contrasena_hash)

    def obtener_todos(self) -> list[Usuario]:
        logger.info("Obteniendo todos los usuarios")
        return self.sesion.query(Usuario).all()

    def buscar_por_rol(
        self, rol: RolUsuario, activo: bool = None, limite: int = None, offset: int = None
    ):
        logger.info(f"Buscando usuarios por rol: {rol.value}")
        query = self.sesion.query(Usuario).filter(Usuario.rol == rol)
        if activo is not None:
            query = query.filter(Usuario.activo == activo)
        query = query.order_by(Usuario.fecha_registro.desc())
        if limite:
            query = query.limit(limite)
        if offset:
            query = query.offset(offset)
        return query.all()

    def contar_por_rol(self, rol: RolUsuario, activo: bool = None) -> int:
        query = self.sesion.query(Usuario).filter(Usuario.rol == rol)
        if activo is not None:
            query = query.filter(Usuario.activo == activo)
        return query.count()

    def buscar_por_rol_y_busqueda(
        self, rol: RolUsuario, busqueda: str, limite: int = None, offset: int = None
    ):
        logger.info(f"Buscando usuarios por rol y búsqueda: {rol.value}, término: {busqueda}")
        query = self.sesion.query(Usuario).filter(Usuario.rol == rol)
        if busqueda:
            query = query.filter(
                (Usuario.nombre.ilike(f"%{busqueda}%"))
                | (Usuario.apellido.ilike(f"%{busqueda}%"))
                | (Usuario.email.ilike(f"%{busqueda}%"))
            )
        query = query.order_by(Usuario.fecha_registro.desc())
        if limite:
            query = query.limit(limite)
        if offset:
            query = query.offset(offset)
        return query.all()

    def actualizar_usuario(
        self,
        usuario: Usuario,
        nombre: str = None,
        apellido: str = None,
        email: str = None,
        telefono: str = None,
        biografia: str = None,
        especialidad: str = None,
        contrasena: str = None,
    ) -> Usuario:
        logger.info(f"Actualizando usuario ID: {usuario.id}")
        if nombre is not None:
            usuario.nombre = nombre
        if apellido is not None:
            usuario.apellido = apellido
        if email is not None:
            usuario.email = email
        if telefono is not None:
            usuario.telefono = telefono
        if biografia is not None:
            usuario.biografia = biografia
        if especialidad is not None:
            usuario.especialidad = especialidad
        if contrasena is not None:
            usuario.contrasena_hash = hash_contrasena(contrasena)
        self.sesion.commit()
        self.sesion.refresh(usuario)
        logger.info(f"Usuario actualizado exitosamente: {usuario.id}")
        return usuario

    def desactivar_usuario(self, usuario: Usuario) -> bool:
        logger.info(f"Desactivando usuario ID: {usuario.id}")
        usuario.activo = False
        self.sesion.commit()
        logger.info(f"Usuario desactivado: {usuario.id}")
        return True

    def email_existe_excepto_id(self, email: str, exclude_id: int) -> bool:
        return (
            self.sesion.query(Usuario)
            .filter(Usuario.email == email, Usuario.id != exclude_id)
            .first()
            is not None
        )
