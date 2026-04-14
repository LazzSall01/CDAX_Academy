from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import obtener_configuracion
from app.logs import logger

config = obtener_configuracion()

logger.info(f"Inicializando conexión a base de datos: {config.DATABASE_URL}")

if config.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        config.DATABASE_URL, connect_args={"check_same_thread": False}, echo=config.MODO_DESARROLLO
    )
else:
    engine = create_engine(
        config.DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20, echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def obtener_sesion():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def iniciar_base_datos():
    logger.info("Creando tablas en base de datos")
    Base.metadata.create_all(bind=engine)

    from app.modelos import Usuario, RolUsuario
    from app.servicios.auth_servicio import AuthServicio

    sesion = SessionLocal()
    try:
        admin_existente = (
            sesion.query(Usuario).filter(Usuario.email == "admin@cdaxacademy.com").first()
        )

        if not admin_existente:
            logger.info("Creando usuario administrador por defecto")
            auth_servicio = AuthServicio(sesion)
            admin = auth_servicio.registrar_usuario(
                email="admin@cdaxacademy.com",
                contrasena="admin123",
                nombre="Admin",
                apellido="CDAX",
                rol=RolUsuario.ADMIN,
            )
            logger.info(f"Usuario admin creado con ID: {admin.id}")
        else:
            logger.info("Usuario admin ya existe")
    finally:
        sesion.close()

    logger.info("Base de datos inicializada correctamente")
