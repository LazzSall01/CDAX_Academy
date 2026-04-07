from sqlalchemy.orm import Session
from app.repositorios import FaqRepositorio
from app.logs import logger
from typing import List


class FaqServicio:
    def __init__(self, sesion: Session):
        self.sesion = sesion
        self.repo = FaqRepositorio(sesion)

    def obtener_todos(self) -> List:
        logger.info("Obteniendo todas las FAQs")
        return self.repo.obtener_todos()

    def obtener_por_categoria(self, categoria: str) -> List:
        return self.repo.obtener_por_categoria(categoria)

    def crear_faq(self, pregunta: str, respuesta: str, categoria: str = None, orden: int = 0):
        return self.repo.crear(pregunta, respuesta, categoria, orden)
