from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class EstadoSuscripcion(enum.Enum):
    ACTIVO = "ACTIVO"
    CANCELADO = "CANCELADO"
    PENDIENTE = "PENDIENTE"


class EstadoPago(enum.Enum):
    PENDIENTE = "PENDIENTE"
    COMPLETADO = "COMPLETADO"
    FALLIDO = "FALLIDO"


class TipoPrograma(enum.Enum):
    CURSO = "CURSO"
    DIPLOMADO = "DIPLOMADO"
    ESPECIALIDAD = "ESPECIALIDAD"


class EstadoInscripcion(enum.Enum):
    PROXIMAMENTE = "PROXIMAMENTE"
    INSCRIPCIONES_ABIERTAS = "INSCRIPCIONES_ABIERTAS"
    CUPO_LIMITADO = "CUPO_LIMITADO"
    AGOTADO = "AGOTADO"


class EstadoAprobacion(enum.Enum):
    APROBADO = "APROBADO"
    PENDIENTE = "PENDIENTE"
    RECHAZADO = "RECHAZADO"


class Curso(Base):
    __tablename__ = "cursos"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    descripcion_larga = Column(Text, nullable=True)
    precio = Column(Integer, nullable=False)
    precio_pendiente = Column(Integer, nullable=True)
    estado_aprobacion = Column(String(20), default="APROBADO")
    stripe_price_id = Column(String(100), nullable=True)
    imagen_url = Column(String(500), nullable=True)
    capacidad_maxima = Column(Integer, default=30)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())

    # Nuevos campos para programas
    tipo_programa = Column(String(50), default="CURSO", index=True)
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin_inscripcion = Column(Date, nullable=True)
    estado_inscripcion = Column(String(50), default="PROXIMAMENTE", index=True)
    whatsapp_contacto = Column(String(20), nullable=True)
    duracion_horas = Column(Integer, nullable=True)
    incluye_diploma = Column(Boolean, default=True)
    requisitos_admision = Column(Text, nullable=True)
    modalidad = Column(String(50), default="EN_LINEA", index=True)
    incluye_materiales = Column(Boolean, default=True)

    modulos = relationship("Modulo", back_populates="curso", order_by="Modulo.orden")
    suscripciones = relationship("Suscripcion", back_populates="curso")
    temas_foro = relationship("ForoTema", back_populates="curso")
    instructores = relationship("CursoInstructor", back_populates="curso")
