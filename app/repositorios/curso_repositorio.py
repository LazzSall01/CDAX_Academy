from sqlalchemy.orm import Session
from sqlalchemy import func
from app.modelos import Curso, Modulo, Leccion
from app.logs import logger
from typing import Optional
from slugify import slugify


class CursoRepositorio:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def buscar_por_slug(self, slug: str) -> Optional[Curso]:
        logger.info(f"Buscando curso por slug: {slug}")
        return self.sesion.query(Curso).filter(Curso.slug == slug).first()

    def buscar_por_id(self, curso_id: int) -> Optional[Curso]:
        logger.info(f"Buscando curso por ID: {curso_id}")
        return self.sesion.query(Curso).filter(Curso.id == curso_id).first()

    def obtener_todos_activos(self) -> list[Curso]:
        logger.info("Obteniendo todos los cursos activos")
        return self.sesion.query(Curso).filter(Curso.activo == True).all()

    def crear_curso(
        self, titulo: str, descripcion: str, precio: int, imagen_url: Optional[str] = None
    ) -> Curso:
        logger.info(f"Creando curso: {titulo}")
        slug = slugify(titulo)
        curso = Curso(
            titulo=titulo, slug=slug, descripcion=descripcion, precio=precio, imagen_url=imagen_url
        )
        self.sesion.add(curso)
        self.sesion.commit()
        self.sesion.refresh(curso)
        logger.info(f"Curso creado exitosamente con ID: {curso.id}")
        return curso

    def obtener_modulos_con_lecciones(self, curso_id: int) -> list[Modulo]:
        logger.info(f"Obteniendo módulos con lecciones para curso ID: {curso_id}")
        return (
            self.sesion.query(Modulo)
            .filter(Modulo.curso_id == curso_id)
            .order_by(Modulo.orden)
            .all()
        )

    def buscar_leccion_por_id(self, leccion_id: int) -> Optional[Leccion]:
        logger.info(f"Buscando lección por ID: {leccion_id}")
        return self.sesion.query(Leccion).filter(Leccion.id == leccion_id).first()

    def obtener_por_tipo(self, tipo: str) -> list[Curso]:
        logger.info(f"Obteniendo cursos por tipo: {tipo}")
        return (
            self.sesion.query(Curso).filter(Curso.activo == True, Curso.tipo_programa == tipo).all()
        )
