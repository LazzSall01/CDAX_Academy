import stripe
from sqlalchemy.orm import Session
from app.config import obtener_configuracion
from app.logs import logger

config = obtener_configuracion()
stripe.api_key = config.STRIPE_SECRET_KEY


class PagoServicio:
    def __init__(self, sesion: Session):
        self.sesion = sesion
        self.stripe = stripe

    def verificar_webhook(self, payload: bytes, signature: str) -> dict:
        logger.info("Verificando webhook de Stripe")
        try:
            evento = stripe.Webhook.construct_event(
                payload, signature, config.STRIPE_WEBHOOK_SECRET
            )
            logger.info(f"Webhook verificado: {evento['type']}")
            return evento
        except ValueError as e:
            logger.error(f"Payload inválido: {e}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Signature inválida: {e}")
            raise

    def procesar_checkout_completado(self, evento: dict):
        logger.info("Procesando checkout.session.completed")
        session = evento["data"]["object"]
        curso_id = int(session.get("metadata", {}).get("curso_id", 0))
        usuario_id = int(session.get("metadata", {}).get("usuario_id", 0))

        if curso_id and usuario_id:
            logger.info(f"Procesando pago completado: curso={curso_id}, usuario={usuario_id}")
            from app.servicios.curso_servicio import CursoServicio

            servicio = CursoServicio(self.sesion)
            servicio.verificar_y_activar_suscripcion(session["id"], usuario_id, curso_id)
