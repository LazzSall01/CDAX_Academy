import stripe
from sqlalchemy.orm import Session
from datetime import datetime
from app.config import obtener_configuracion
from app.logs import logger
from app.repositorios import CursoRepositorio
from app.modelos import Suscripcion, EstadoSuscripcion

config = obtener_configuracion()
stripe.api_key = config.STRIPE_SECRET_KEY


class CursoServicio:
    def __init__(self, sesion: Session):
        self.sesion = sesion
        self.curso_repo = CursoRepositorio(sesion)

    def obtener_todos_los_cursos(self) -> list:
        logger.info("Obteniendo todos los cursos")
        return self.curso_repo.obtener_todos_activos()

    def obtener_curso_por_slug(self, slug: str):
        logger.info(f"Obteniendo curso por slug: {slug}")
        return self.curso_repo.buscar_por_slug(slug)

    def obtener_curso_por_id(self, curso_id: int):
        logger.info(f"Obteniendo curso por ID: {curso_id}")
        return self.curso_repo.buscar_por_id(curso_id)

    def obtener_modulos_y_lecciones(self, curso_id: int):
        logger.info(f"Obteniendo módulos y lecciones para curso ID: {curso_id}")
        modulos = self.curso_repo.obtener_modulos_con_lecciones(curso_id)
        resultado = []
        for modulo in modulos:
            lecciones_data = []
            for leccion in modulo.lecciones:
                lecciones_data.append(
                    {
                        "id": leccion.id,
                        "titulo": leccion.titulo,
                        "descripcion": leccion.descripcion,
                        "video_url": leccion.video_url,
                        "duracion_minutos": leccion.duracion_minutos,
                        "orden": leccion.orden,
                    }
                )
            resultado.append(
                {
                    "id": modulo.id,
                    "titulo": modulo.titulo,
                    "orden": modulo.orden,
                    "lecciones": lecciones_data,
                }
            )
        return resultado

    def crear_sesion_stripe_checkout(self, curso_id: int, usuario_id: int, dominio: str) -> str:
        logger.info(f"Creando sesión de Stripe para curso {curso_id}, usuario {usuario_id}")
        curso = self.curso_repo.buscar_por_id(curso_id)
        if not curso:
            logger.error(f"Curso no encontrado: {curso_id}")
            raise ValueError("Curso no encontrado")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": curso.titulo,
                            "description": curso.descripcion,
                        },
                        "unit_amount": curso.precio,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=f"{dominio}/pago/exitoso?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{dominio}/curso/{curso.slug}",
            metadata={
                "curso_id": str(curso_id),
                "usuario_id": str(usuario_id),
            },
        )
        logger.info(f"Stripe checkout session creada: {session.id}")
        return session.url

    def verificar_y_activar_suscripcion(self, session_id: str, usuario_id: int, curso_id: int):
        logger.info(f"Verificando sesión {session_id} y activando suscripción")
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == "paid":
            suscripcion = Suscripcion(
                usuario_id=usuario_id,
                curso_id=curso_id,
                stripe_subscription_id=session.id,
                estado=EstadoSuscripcion.ACTIVO,
                fecha_inicio=datetime.utcnow(),
                fecha_fin=None,
            )
            self.sesion.add(suscripcion)
            self.sesion.commit()
            logger.info(f"Suscripción activada para usuario {usuario_id}, curso {curso_id}")
            return True

        logger.warning(f"Pago no completado para sesión {session_id}")
        return False

    def verificar_acceso_curso(self, usuario_id: int, curso_id: int) -> bool:
        logger.info(f"Verificando acceso al curso {curso_id} para usuario {usuario_id}")
        suscripcion = (
            self.sesion.query(Suscripcion)
            .filter(
                Suscripcion.usuario_id == usuario_id,
                Suscripcion.curso_id == curso_id,
                Suscripcion.estado == EstadoSuscripcion.ACTIVO,
            )
            .first()
        )
        acceso = suscripcion is not None
        logger.info(f"Acceso {'permitido' if acceso else 'denegado'}")
        return acceso

    def obtener_cursos_por_tipo(self, tipo: str) -> list:
        logger.info(f"Obteniendo cursos por tipo: {tipo}")
        return self.curso_repo.obtener_por_tipo(tipo)
