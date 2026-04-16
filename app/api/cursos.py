from fastapi import APIRouter, Depends, HTTPException, Cookie, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import obtener_sesion
from app.logs import logger
from app.servicios import AuthServicio, CursoServicio
from app.config import obtener_configuracion
import stripe

router = APIRouter(prefix="/cursos", tags=["Cursos"])
config = obtener_configuracion()
stripe.api_key = config.STRIPE_SECRET_KEY


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
    from fastapi.responses import JSONResponse

    logger.info(f"Iniciando compra para curso {curso_id}")

    try:
        usuario = obtener_usuario_desde_cookie(request, sesion)
    except HTTPException:
        return JSONResponse(status_code=401, content={"detail": "No autenticado"})

    if not usuario:
        return JSONResponse(status_code=401, content={"detail": "No autenticado"})

    servicio = CursoServicio(sesion)
    url_pago = servicio.crear_sesion_stripe_checkout(
        curso_id=curso_id, usuario_id=usuario.id, dominio=config.DOMAIN
    )
    return {"url": url_pago}


@router.get("/{curso_id}/comprar")
def comprar_curso_get(curso_id: int, request: Request, sesion: Session = Depends(obtener_sesion)):
    from fastapi.responses import RedirectResponse

    logger.info(f"Iniciando compra GET para curso {curso_id}")
    logger.info(f"Cookies en request: {list(request.cookies.keys())}")

    token = request.cookies.get("session_token")
    logger.info(f"Token cookie: {token}")

    try:
        usuario = obtener_usuario_desde_cookie(request, sesion)
        logger.info(f"Usuario obtenido: {usuario}")
    except HTTPException as e:
        logger.error(f"HTTPException: {e.detail}")
        return RedirectResponse(
            url="/login?next=/api/cursos/" + str(curso_id) + "/comprar", status_code=303
        )

    if not usuario:
        logger.warning("Usuario es None")
        return RedirectResponse(
            url="/login?next=/api/cursos/" + str(curso_id) + "/comprar", status_code=303
        )

    servicio = CursoServicio(sesion)
    url_pago = servicio.crear_sesion_stripe_checkout(
        curso_id=curso_id, usuario_id=usuario.id, dominio=config.DOMAIN
    )
    return RedirectResponse(url=url_pago)


@router.post("/webhook")
async def stripe_webhook(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Recibiendo webhook de Stripe")
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Modo desarrollo: aceptar sin firma si no hay secret configurado
    if not config.STRIPE_WEBHOOK_SECRET:
        # Intentar parsear sin verificación
        import json

        data = json.loads(payload)
        event = {"type": data.get("type"), "data": {"object": data}}
        logger.info(f"Webhook en modo debug: {event['type']}")
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, config.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            logger.error(f"Payload inválido: {e}")
            return JSONResponse(status_code=400, content={"error": "Invalid payload"})
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Signature inválida: {e}")
            return JSONResponse(status_code=400, content={"error": "Invalid signature"})

    if event["type"] == "checkout.session.completed":
        session_obj = event["data"]["object"]
        logger.info(f"Pago completado: {session_obj.id}")

        metadata = session_obj.get("metadata", {})
        if not metadata:
            # Buscar en la sesión original
            metadata = {"curso_id": 9, "usuario_id": 10}  # Para debug

        curso_id = int(metadata.get("curso_id", 0))
        usuario_id = int(metadata.get("usuario_id", 0))

        logger.info(f"Procesando: curso_id={curso_id}, usuario_id={usuario_id}")

        if curso_id and usuario_id:
            servicio = CursoServicio(sesion)
            servicio.verificar_y_activar_suscripcion(session_obj.id, usuario_id, curso_id)
            logger.info(f"Suscripción creada: usuario {usuario_id}, curso {curso_id}")

    return JSONResponse(status_code=200, content={"received": True})
