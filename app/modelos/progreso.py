from sqlalchemy import Column, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ProgresoLeccion(Base):
    __tablename__ = "progreso_lecciones"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    leccion_id = Column(Integer, ForeignKey("lecciones.id"), nullable=False, index=True)
    completado = Column(Boolean, default=False)
    fecha_completado = Column(DateTime(timezone=True), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("Usuario", back_populates="progreso_lecciones")
    leccion = relationship("Leccion", back_populates="progreso")
