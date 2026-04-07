from sqlalchemy.orm import Session
from app.modelos import ForoTema, ForoRespuesta
from app.logs import logger
from typing import Optional


class ForoRepositorio:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def buscar_tema_por_id(self, tema_id: int) -> Optional[ForoTema]:
        logger.info(f"Buscando tema de foro por ID: {tema_id}")
        return self.sesion.query(ForoTema).filter(ForoTema.id == tema_id).first()

    def obtener_temas_por_curso(self, curso_id: int) -> list[ForoTema]:
        logger.info(f"Obteniendo temas de foro para curso ID: {curso_id}")
        return (
            self.sesion.query(ForoTema)
            .filter(ForoTema.curso_id == curso_id)
            .order_by(ForoTema.fecha_creacion.desc())
            .all()
        )

    def crear_tema(self, curso_id: int, usuario_id: int, titulo: str, contenido: str) -> ForoTema:
        logger.info(f"Creando tema de foro: {titulo}")
        tema = ForoTema(
            curso_id=curso_id, usuario_id=usuario_id, titulo=titulo, contenido=contenido
        )
        self.sesion.add(tema)
        self.sesion.commit()
        self.sesion.refresh(tema)
        logger.info(f"Tema creado exitosamente con ID: {tema.id}")
        return tema

    def obtener_respuestas_tema(self, tema_id: int) -> list[ForoRespuesta]:
        logger.info(f"Obteniendo respuestas para tema ID: {tema_id}")
        return (
            self.sesion.query(ForoRespuesta)
            .filter(ForoRespuesta.tema_id == tema_id)
            .order_by(ForoRespuesta.fecha_creacion.asc())
            .all()
        )

    def crear_respuesta(self, tema_id: int, usuario_id: int, contenido: str) -> ForoRespuesta:
        logger.info(f"Creando respuesta para tema ID: {tema_id}")
        respuesta = ForoRespuesta(tema_id=tema_id, usuario_id=usuario_id, contenido=contenido)
        self.sesion.add(respuesta)
        self.sesion.commit()
        self.sesion.refresh(respuesta)
        logger.info(f"Respuesta creada exitosamente con ID: {respuesta.id}")
        return respuesta
