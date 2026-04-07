from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class ConfiguracionBunny(Base):
    __tablename__ = "configuracion_bunny"

    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(Text, nullable=False)
    library_id = Column(String(50), nullable=False)
    storage_zone = Column(String(100), nullable=True)
    hostname = Column(String(255), nullable=False)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())
