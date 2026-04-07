from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class EstadoSuscripcion(enum.Enum):
    ACTIVO = "ACTIVO"
    CANCELADO = "CANCELADO"
    PENDIENTE = "PENDIENTE"


class Suscripcion(Base):
    __tablename__ = "suscripciones"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=False)
    stripe_subscription_id = Column(String(100), nullable=True)
    estado = Column(SQLEnum(EstadoSuscripcion), default=EstadoSuscripcion.PENDIENTE)
    fecha_inicio = Column(DateTime(timezone=True), nullable=True)
    fecha_fin = Column(DateTime(timezone=True), nullable=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("Usuario", back_populates="suscripciones")
    curso = relationship("Curso", back_populates="suscripciones")
