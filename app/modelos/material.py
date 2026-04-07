from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Material(Base):
    __tablename__ = "materiales"

    id = Column(Integer, primary_key=True, index=True)
    leccion_id = Column(Integer, ForeignKey("lecciones.id"), nullable=False)
    titulo = Column(String(255), nullable=False)
    tipo_archivo = Column(String(50), nullable=False)  # PDF, DOC, ZIP, IMG, etc.
    url = Column(String(500), nullable=False)
    tamanho_bytes = Column(Integer, default=0)
    nombre_original = Column(String(255), nullable=True)
    fecha_subida = Column(DateTime(timezone=True), server_default=func.now())
    usuario_subio_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    leccion = relationship("Leccion", back_populates="materiales")
