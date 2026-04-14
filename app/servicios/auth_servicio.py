import httpx
from datetime import datetime, timedelta
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.config import obtener_configuracion
from app.logs import logger
from app.repositorios import UsuarioRepositorio
from app.modelos import RolUsuario
from typing import Optional

config = obtener_configuracion()
ALGORITHM = "HS256"


class AuthServicio:
    def __init__(self, sesion: Session):
        self.sesion = sesion
        self.usuario_repo = UsuarioRepositorio(sesion)

    def generar_url_autorizacion(self, estado: str) -> str:
        logger.info("Generando URL de autorización Google OAuth2")
        params = {
            "client_id": config.GOOGLE_CLIENT_ID,
            "redirect_uri": config.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": estado,
        }
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query}"

    def intercambiar_codigo_por_tokens(self, codigo: str) -> dict:
        logger.info("Intercambiando código por tokens")
        data = {
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "code": codigo,
            "grant_type": "authorization_code",
            "redirect_uri": config.GOOGLE_REDIRECT_URI,
        }
        with httpx.Client() as cliente:
            respuesta = cliente.post(config.GOOGLE_TOKEN_URL, data=data)
            respuesta.raise_for_status()
            tokens = respuesta.json()
            logger.info("Tokens obtenidos correctamente")
            return tokens

    def obtener_info_usuario(self, access_token: str) -> dict:
        logger.info("Obteniendo información del usuario de Google")
        headers = {"Authorization": f"Bearer {access_token}"}
        with httpx.Client() as cliente:
            respuesta = cliente.get(config.GOOGLE_USER_INFO_URL, headers=headers)
            respuesta.raise_for_status()
            info = respuesta.json()
            logger.info(f"Usuario obtenido: {info.get('email')}")
            return info

    def crear_actualizar_usuario(self, info_google: dict, google_id: str) -> object:
        logger.info(f"Creando/actualizando usuario: {info_google.get('email')}")
        usuario_existente = self.usuario_repo.buscar_por_google_id(google_id)

        if usuario_existente:
            logger.info(f"Usuario existente encontrado: {usuario_existente.id}")
            return usuario_existente

        email = info_google.get("email")
        nombre = info_google.get("given_name", "Usuario")
        apellido = info_google.get("family_name", "")
        avatar_url = info_google.get("picture")

        usuario = self.usuario_repo.crear_usuario_google(
            google_id=google_id,
            email=email,
            nombre=nombre,
            apellido=apellido,
            avatar_url=avatar_url,
        )
        return usuario

    def registrar_usuario(
        self,
        email: str,
        contrasena: str,
        nombre: str,
        apellido: str,
        rol: RolUsuario = None,
        usuario_nombre: str = None,
    ) -> object:
        logger.info(f"Registrando nuevo usuario: {email}")

        usuario_existente = self.usuario_repo.buscar_por_email(email)
        if usuario_existente:
            logger.warning(f"Usuario ya existe: {email}")
            raise ValueError("El email ya está registrado")

        if usuario_nombre:
            usuario_existente = self.usuario_repo.buscar_por_usuario(usuario_nombre)
            if usuario_existente:
                logger.warning(f"Usuario ya existe: {usuario_nombre}")
                raise ValueError("El nombre de usuario ya está registrado")

        usuario = self.usuario_repo.crear_usuario_email(
            email=email,
            contrasena=contrasena,
            nombre=nombre,
            apellido=apellido,
            rol=rol,
            usuario=usuario_nombre,
        )
        return usuario

    def login_email(self, email: str, contrasena: str) -> Optional[object]:
        logger.info(f"Intentando login con email: {email}")

        usuario = self.usuario_repo.buscar_por_email(email)
        if not usuario:
            # También buscar por nombre de usuario
            logger.info(f"Buscando por nombre de usuario: {email}")
            usuario = self.usuario_repo.buscar_por_usuario(email)
        if not usuario:
            logger.warning(f"Usuario no encontrado: {email}")
            return None

        if not self.usuario_repo.verificar_contrasena(usuario, contrasena):
            logger.warning(f"Contraseña incorrecta para: {email}")
            return None

        logger.info(f"Login exitoso para: {email}")
        return usuario

    def generar_token_jwt(self, usuario_id: int, rol: RolUsuario) -> str:
        logger.info(f"Generando JWT para usuario ID: {usuario_id}")
        expiracion = datetime.utcnow() + timedelta(hours=24)
        payload = {"sub": str(usuario_id), "rol": rol.value, "exp": expiracion}
        token = jwt.encode(payload, config.SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"JWT generado exitosamente")
        return token

    def verificar_token_jwt(self, token: str) -> dict:
        logger.info("Verificando token JWT")
        try:
            payload = jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITHM])
            logger.info("Token verificado exitosamente")
            return payload
        except JWTError as e:
            logger.error(f"Error al verificar token: {e}")
            raise

    def obtener_usuario_actual(self, token: str) -> object:
        payload = self.verificar_token_jwt(token)
        usuario_id = int(payload.get("sub"))
        usuario = self.usuario_repo.buscar_por_id(usuario_id)
        if not usuario:
            logger.error(f"Usuario no encontrado: {usuario_id}")
            raise ValueError("Usuario no encontrado")
        return usuario
