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
    ) -> Usuario:
        logger.info(f"Creando nuevo usuario con email: {email}")
        contrasena_hash = hash_contrasena(contrasena)
        if rol is None:
            rol = RolUsuario.ALUMNO
        usuario = Usuario(
            email=email,
            contrasena_hash=contrasena_hash,
            nombre=nombre,
            apellido=apellido,
            rol=rol,
        )
        self.sesion.add(usuario)
        self.sesion.commit()
        self.sesion.refresh(usuario)
        logger.info(f"Usuario creado exitosamente con ID: {usuario.id}, rol: {rol.value}")
        return usuario

    def verificar_contrasena(self, usuario: Usuario, contrasena: str) -> bool:
        if not usuario.contrasena_hash:
            return False
        return verificar_contrasena_hash(contrasena, usuario.contrasena_hash)

    def obtener_todos(self) -> list[Usuario]:
        logger.info("Obteniendo todos los usuarios")
        return self.sesion.query(Usuario).all()
