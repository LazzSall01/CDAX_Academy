from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Modulo(Base):
    __tablename__ = "modulos"

    id = Column(Integer, primary_key=True, index=True)
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=False)
    titulo = Column(String(255), nullable=False)
    orden = Column(Integer, nullable=False)

    curso = relationship("Curso", back_populates="modulos")
    lecciones = relationship("Leccion", back_populates="modulo", order_by="Leccion.orden")
