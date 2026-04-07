from sqlalchemy.orm import Session
from app.logs import logger
from app.repositorios import ForoRepositorio


class ForoServicio:
    def __init__(self, sesion: Session):
        self.sesion = sesion
        self.foro_repo = ForoRepositorio(sesion)

    def obtener_temas_curso(self, curso_id: int) -> list:
        logger.info(f"Obteniendo temas del curso {curso_id}")
        return self.foro_repo.obtener_temas_por_curso(curso_id)

    def obtener_tema(self, tema_id: int):
        logger.info(f"Obteniendo tema {tema_id}")
        return self.foro_repo.buscar_tema_por_id(tema_id)

    def crear_tema(self, curso_id: int, usuario_id: int, titulo: str, contenido: str):
        logger.info(f"Creando tema en curso {curso_id}")
        return self.foro_repo.crear_tema(curso_id, usuario_id, titulo, contenido)

    def obtener_respuestas(self, tema_id: int) -> list:
        logger.info(f"Obteniendo respuestas del tema {tema_id}")
        return self.foro_repo.obtener_respuestas_tema(tema_id)

    def crear_respuesta(self, tema_id: int, usuario_id: int, contenido: str):
        logger.info(f"Creando respuesta en tema {tema_id}")
        return self.foro_repo.crear_respuesta(tema_id, usuario_id, contenido)
