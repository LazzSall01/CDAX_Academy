from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import obtener_sesion
from app.logs import logger
from app.servicios import PagoServicio

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/stripe")
async def webhook_stripe(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Recibiendo webhook de Stripe")
    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    if not signature:
        logger.warning("Falta signature de Stripe")
        raise HTTPException(status_code=400, detail="Falta firma")

    try:
        pago_servicio = PagoServicio(sesion)
        evento = pago_servicio.verificar_webhook(payload, signature)

        tipo = evento["type"]
        if tipo == "checkout.session.completed":
            pago_servicio.procesar_checkout_completado(evento)
            logger.info("Webhook procesado exitosamente")
        else:
            logger.info(f"Evento ignorado: {tipo}")

        return JSONResponse(content={"status": "success"})
    except ValueError as e:
        logger.error(f"Error al verificar webhook: {e}")
        raise HTTPException(status_code=400, detail="Payload inválido")
    except Exception as e:
        logger.error(f"Error al procesar webhook: {e}")
        raise HTTPException(status_code=500, detail="Error interno")
