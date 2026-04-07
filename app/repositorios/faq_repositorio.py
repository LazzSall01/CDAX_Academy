from sqlalchemy.orm import Session
from app.modelos.faq import Faq
from app.logs import logger
from typing import Optional, List


class FaqRepositorio:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def crear(self, pregunta: str, respuesta: str, categoria: str = None, orden: int = 0) -> Faq:
        logger.info(f"Creando FAQ: {pregunta[:50]}...")
        faq = Faq(pregunta=pregunta, respuesta=respuesta, categoria=categoria, orden=orden)
        self.sesion.add(faq)
        self.sesion.commit()
        self.sesion.refresh(faq)
        return faq

    def obtener_todos(self, activos_only: bool = True) -> List[Faq]:
        logger.info("Obteniendo todas las FAQs")
        query = self.sesion.query(Faq)
        if activos_only:
            query = query.filter(Faq.activo == True)
        return query.order_by(Faq.orden).all()

    def obtener_por_categoria(self, categoria: str) -> List[Faq]:
        return (
            self.sesion.query(Faq)
            .filter(Faq.categoria == categoria, Faq.activo == True)
            .order_by(Faq.orden)
            .all()
        )

    def obtener_por_id(self, faq_id: int) -> Optional[Faq]:
        return self.sesion.query(Faq).filter(Faq.id == faq_id).first()
