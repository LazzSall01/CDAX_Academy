from sqlalchemy.orm import Session
from app.modelos.instructor import Instructor, CursoInstructor
from app.logs import logger
from typing import Optional, List


class InstructorRepositorio:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def crear(
        self,
        nombre: str,
        apellido: str,
        bio: str = None,
        foto_url: str = None,
        especialidad: str = None,
        linkedin_url: str = None,
        email: str = None,
    ) -> Instructor:
        logger.info(f"Creando instructor: {nombre} {apellido}")
        instructor = Instructor(
            nombre=nombre,
            apellido=apellido,
            bio=bio,
            foto_url=foto_url,
            especialidad=especialidad,
            linkedin_url=linkedin_url,
            email=email,
        )
        self.sesion.add(instructor)
        self.sesion.commit()
        self.sesion.refresh(instructor)
        return instructor

    def obtener_todos(self) -> List[Instructor]:
        logger.info("Obteniendo todos los instructores")
        return self.sesion.query(Instructor).filter(Instructor.activo == True).all()

    def obtener_por_id(self, instructor_id: int) -> Optional[Instructor]:
        return self.sesion.query(Instructor).filter(Instructor.id == instructor_id).first()

    def asignar_a_curso(self, curso_id: int, instructor_id: int):
        logger.info(f"Asignando instructor {instructor_id} al curso {curso_id}")
        relacion = CursoInstructor(curso_id=curso_id, instructor_id=instructor_id)
        self.sesion.add(relacion)
        self.sesion.commit()

    def obtener_instructores_curso(self, curso_id: int) -> List[Instructor]:
        logger.info(f"Obteniendo instructores del curso {curso_id}")
        relaciones = (
            self.sesion.query(CursoInstructor).filter(CursoInstructor.curso_id == curso_id).all()
        )
        return [r.instructor for r in relaciones]

    def obtener_cursos_instructor(self, instructor_id: int) -> List[CursoInstructor]:
        return (
            self.sesion.query(CursoInstructor)
            .filter(CursoInstructor.instructor_id == instructor_id)
            .all()
        )
