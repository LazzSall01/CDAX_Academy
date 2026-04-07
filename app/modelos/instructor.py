from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class Instructor(Base):
    __tablename__ = "instructores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    bio = Column(Text, nullable=True)
    foto_url = Column(String(500), nullable=True)
    especialidad = Column(String(200), nullable=True)
    linkedin_url = Column(String(300), nullable=True)
    email = Column(String(200), nullable=True)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, nullable=True)

    cursos = relationship("CursoInstructor", back_populates="instructor")


class CursoInstructor(Base):
    __tablename__ = "curso_instructores"

    id = Column(Integer, primary_key=True, index=True)
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=False)
    instructor_id = Column(Integer, ForeignKey("instructores.id"), nullable=False)

    curso = relationship("Curso", back_populates="instructores")
    instructor = relationship("Instructor", back_populates="cursos")
