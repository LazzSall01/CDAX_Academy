from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import obtener_sesion
from app.logs import logger
from app.servicios import AuthServicio
from app.modelos import Usuario, RolUsuario

router = APIRouter(prefix="/auth", tags=["Autenticación"])


class RegistroRequest(BaseModel):
    email: str
    contrasena: str
    nombre: str
    apellido: str
    usuario: str | None = None


class LoginRequest(BaseModel):
    email: str
    contrasena: str


@router.post("/registro")
def registro(
    email: str = Form(...),
    contrasena: str = Form(...),
    nombre: str = Form(...),
    apellido: str = Form(...),
    usuario: str = Form(None),
    sesion: Session = Depends(obtener_sesion),
):
    logger.info(f"Registro solicitado para: {email}")
    auth_servicio = AuthServicio(sesion)

    try:
        usuario = auth_servicio.registrar_usuario(
            email=email,
            contrasena=contrasena,
            nombre=nombre,
            apellido=apellido,
            usuario_nombre=usuario,
        )

        token_jwt = auth_servicio.generar_token_jwt(usuario.id, usuario.rol)

        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(
            key="session_token",
            value=token_jwt,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=86400,
        )
        logger.info(f"Usuario registrado y autenticado: {usuario.email}")
        return response

    except ValueError as e:
        logger.error(f"Error en registro: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login(
    email: str = Form(...),
    contrasena: str = Form(...),
    session_id: str | None = Form(None),
    sesion: Session = Depends(obtener_sesion),
):
    from fastapi.responses import RedirectResponse
    from app.servicios import CursoServicio
    from app.config import obtener_configuracion
    import stripe

    logger.info(f"Login solicitado para: {email}")
    auth_servicio = AuthServicio(sesion)

    usuario = auth_servicio.login_email(email, contrasena)
    if not usuario:
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    token_jwt = auth_servicio.generar_token_jwt(usuario.id, usuario.rol)

    # Procesar curso comprado si hay session_id
    if session_id:
        try:
            config = obtener_configuracion()
            stripe.api_key = config.STRIPE_SECRET_KEY
            session_obj = stripe.checkout.Session.retrieve(session_id)

            if session_obj.payment_status == "paid":
                metadata = dict(session_obj.metadata) if session_obj.metadata else {}
                curso_id = int(metadata.get("curso_id", 0))

                if curso_id:
                    servicio = CursoServicio(sesion)
                    tiene_acceso = servicio.verificar_acceso_curso(usuario.id, curso_id)
                    if not tiene_acceso:
                        servicio.verificar_y_activar_suscripcion(session_id, usuario.id, curso_id)
                        logger.info(
                            f"Suscripción creada tras login: usuario {usuario.id}, curso {curso_id}"
                        )
        except Exception as e:
            logger.error(f"Error procesando curso tras login: {e}")

    # Redirección según rol
    if usuario.rol == RolUsuario.ADMIN:
        destino = "/admin/dashboard"
    elif usuario.rol == RolUsuario.COORDINADOR:
        destino = "/coordinador/dashboard"
    elif usuario.rol == RolUsuario.PROFESOR:
        destino = "/profesor/dashboard"
    else:
        destino = "/dashboard"

    response = RedirectResponse(url=destino, status_code=303)
    response.set_cookie(
        key="session_token",
        value=token_jwt,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=86400,
    )
    logger.info(f"Usuario autenticado: {usuario.email}, rol: {usuario.rol.value}")
    return response


@router.get("/google")
def login_google(sesion: Session = Depends(obtener_sesion)):
    logger.info("Iniciando flujo OAuth2 con Google")
    auth_servicio = AuthServicio(sesion)
    estado = "login"
    url = auth_servicio.generar_url_autorizacion(estado)
    logger.info(f"Redirigiendo a Google: {url}")
    return RedirectResponse(url)


@router.get("/google/callback")
def callback_google(code: str, state: str, sesion: Session = Depends(obtener_sesion)):
    logger.info(f"Callback recibido con código: {code[:20]}...")
    auth_servicio = AuthServicio(sesion)

    tokens = auth_servicio.intercambiar_codigo_por_tokens(code)
    access_token = tokens["access_token"]

    info_usuario = auth_servicio.obtener_info_usuario(access_token)
    google_id = info_usuario["id"]

    usuario = auth_servicio.crear_actualizar_usuario(info_usuario, google_id)

    token_jwt = auth_servicio.generar_token_jwt(usuario.id, usuario.rol)

    # Redirección según rol
    if usuario.rol == RolUsuario.ADMIN:
        destino = "/admin/dashboard"
    elif usuario.rol == RolUsuario.COORDINADOR:
        destino = "/coordinador/dashboard"
    elif usuario.rol == RolUsuario.PROFESOR:
        destino = "/profesor/dashboard"
    else:
        destino = "/dashboard"

    response = RedirectResponse(url=destino)
    response.set_cookie(
        key="session_token",
        value=token_jwt,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=86400,
    )
    logger.info(f"Usuario {usuario.email} autenticado exitosamente, rol: {usuario.rol.value}")
    return response


@router.get("/demo")
def login_demo(sesion: Session = Depends(obtener_sesion)):
    from jose import jwt
    from datetime import datetime, timedelta

    logger.info("Login demo iniciado")

    usuario = sesion.query(Usuario).filter(Usuario.email == "demo@dental.com").first()
    if not usuario:
        from app.servicios.auth_servicio import AuthServicio

        auth_servicio = AuthServicio(sesion)
        usuario = auth_servicio.registrar_usuario(
            email="demo@dental.com",
            contrasena="demo123",
            nombre="Demo",
            apellido="Usuario",
        )
        logger.info(f"Usuario demo creado: {usuario.id}")

    from app.config import obtener_configuracion

    config = obtener_configuracion()
    payload = {
        "sub": str(usuario.id),
        "rol": usuario.rol.value,
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    token = jwt.encode(payload, config.SECRET_KEY, algorithm="HS256")

    # Redirección según rol
    if usuario.rol == RolUsuario.ADMIN:
        destino = "/admin/dashboard"
    elif usuario.rol == RolUsuario.PROFESOR:
        destino = "/profesor/dashboard"
    else:
        destino = "/dashboard"

    response = RedirectResponse(url=destino)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=86400,
    )
    logger.info(f"Usuario demo autenticado: {usuario.email}")
    return response


@router.get("/demo-estudiante")
def login_demo_estudiante(sesion: Session = Depends(obtener_sesion)):
    from jose import jwt
    from datetime import datetime, timedelta

    logger.info("Login demo estudiante iniciado")

    usuario = sesion.query(Usuario).filter(Usuario.email == "estudiante1@cdax.com").first()
    if not usuario:
        from app.servicios.auth_servicio import AuthServicio

        auth_servicio = AuthServicio(sesion)
        usuario = auth_servicio.registrar_usuario(
            email="estudiante1@cdax.com",
            contrasena="estudiante1",
            nombre="Estudiante",
            apellido="Uno",
            rol=RolUsuario.ALUMNO,
            usuario_nombre="estudiante1",
        )
        logger.info(f"Usuario estudiante creado: {usuario.id}")

    from app.config import obtener_configuracion

    config = obtener_configuracion()
    payload = {
        "sub": str(usuario.id),
        "rol": usuario.rol.value,
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    token = jwt.encode(payload, config.SECRET_KEY, algorithm="HS256")

    response = RedirectResponse(url="/dashboard")
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=86400,
    )
    logger.info(f"Usuario estudiante autenticado: {usuario.email}")
    return response


@router.get("/logout")
def logout():
    logger.info("Cerrando sesión")
    response = RedirectResponse(url="/")
    response.delete_cookie("session_token")
    return response
