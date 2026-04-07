from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class RolUsuario(enum.Enum):
    ADMIN = "ADMIN"
    PROFESOR = "PROFESOR"
    ALUMNO = "ALUMNO"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    contrasena_hash = Column(String(255), nullable=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    rol = Column(SQLEnum(RolUsuario), default=RolUsuario.ALUMNO, nullable=False)
    avatar_url = Column(String(500), nullable=True)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())
    activo = Column(Boolean, default=True)

    # Campos para profesor
    bunny_library_id = Column(String(100), nullable=True)
    telefono = Column(String(20), nullable=True)
    biografia = Column(Text, nullable=True)
    especialidad = Column(String(200), nullable=True)

    suscripciones = relationship("Suscripcion", back_populates="usuario")
    progreso_lecciones = relationship("ProgresoLeccion", back_populates="usuario")
    temas_foro = relationship("ForoTema", back_populates="usuario")
    respuestas_foro = relationship("ForoRespuesta", back_populates="usuario")
