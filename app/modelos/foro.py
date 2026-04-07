from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ForoTema(Base):
    __tablename__ = "foros_temas"

    id = Column(Integer, primary_key=True, index=True)
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    titulo = Column(String(255), nullable=False)
    contenido = Column(Text, nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())

    curso = relationship("Curso", back_populates="temas_foro")
    usuario = relationship("Usuario", back_populates="temas_foro")
    respuestas = relationship("ForoRespuesta", back_populates="tema", cascade="all, delete-orphan")


class ForoRespuesta(Base):
    __tablename__ = "foros_respuestas"

    id = Column(Integer, primary_key=True, index=True)
    tema_id = Column(Integer, ForeignKey("foros_temas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    contenido = Column(Text, nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())

    tema = relationship("ForoTema", back_populates="respuestas")
    usuario = relationship("Usuario", back_populates="respuestas_foro")
