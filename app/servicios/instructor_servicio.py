from sqlalchemy.orm import Session
from app.repositorios import InstructorRepositorio
from app.logs import logger
from typing import List, Optional


class InstructorServicio:
    def __init__(self, sesion: Session):
        self.sesion = sesion
        self.repo = InstructorRepositorio(sesion)

    def obtener_todos(self) -> List:
        logger.info("Obteniendo todos los instructores")
        return self.repo.obtener_todos()

    def obtener_por_id(self, instructor_id: int):
        return self.repo.obtener_por_id(instructor_id)

    def obtener_instructores_curso(self, curso_id: int) -> List:
        return self.repo.obtener_instructores_curso(curso_id)

    def crear_instructor(
        self,
        nombre: str,
        apellido: str,
        bio: str = None,
        foto_url: str = None,
        especialidad: str = None,
        linkedin_url: str = None,
        email: str = None,
    ):
        return self.repo.crear(nombre, apellido, bio, foto_url, especialidad, linkedin_url, email)

    def asignar_a_curso(self, curso_id: int, instructor_id: int):
        self.repo.asignar_a_curso(curso_id, instructor_id)

    def obtener_cursos_instructor(self, instructor_id: int):
        return self.repo.obtener_cursos_instructor(instructor_id)
