from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class EstadoVideo(enum.Enum):
    SIN_SUBIR = "SIN_SUBIR"
    SUBIENDO = "SUBIENDO"
    PROCESANDO = "PROCESANDO"
    LISTO = "LISTO"
    ERROR = "ERROR"


class Leccion(Base):
    __tablename__ = "lecciones"

    id = Column(Integer, primary_key=True, index=True)
    modulo_id = Column(Integer, ForeignKey("modulos.id"), nullable=False)
    titulo = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    video_url = Column(String(500), nullable=True)
    duracion_minutos = Column(Integer, default=0)
    orden = Column(Integer, nullable=False)

    # Campos de Bunny Stream
    bunny_video_id = Column(String(100), nullable=True)
    bunny_thumbnail_url = Column(String(500), nullable=True)
    duracion_segundos = Column(Integer, default=0)
    estado_video = Column(String(20), default="SIN_SUBIR")
    fecha_subida = Column(DateTime(timezone=True), nullable=True)

    # Videos externos (YouTube, Vimeo)
    video_externo_url = Column(String(500), nullable=True)
    tipo_video = Column(String(20), default="BUNNY")  # BUNNY o EXTERNO

    modulo = relationship("Modulo", back_populates="lecciones")
    progreso = relationship("ProgresoLeccion", back_populates="leccion")
    materiales = relationship("Material", back_populates="leccion")
