from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.database import Base


class Faq(Base):
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True)
    pregunta = Column(String(500), nullable=False)
    respuesta = Column(Text, nullable=False)
    categoria = Column(String(100), nullable=True)
    orden = Column(Integer, default=0)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, nullable=True)
