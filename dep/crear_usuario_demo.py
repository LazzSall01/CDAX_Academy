from app.database import SessionLocal
from app.modelos import Usuario, RolUsuario
from app.logs import logger


def crear_usuario_prueba():
    logger.info("Creando usuario de prueba")
    sesion = SessionLocal()

    try:
        usuario_existente = sesion.query(Usuario).filter(Usuario.email == "demo@dental.com").first()
        if usuario_existente:
            logger.info("Usuario demo ya existe")
            return usuario_existente

        usuario = Usuario(
            google_id="demo",
            email="demo@dental.com",
            nombre="Demo",
            apellido="Usuario",
            rol=RolUsuario.ALUMNO,
            activo=True,
        )
        sesion.add(usuario)
        sesion.commit()
        sesion.refresh(usuario)
        logger.info(f"Usuario de prueba creado: {usuario.email}")
        return usuario
    finally:
        sesion.close()


if __name__ == "__main__":
    crear_usuario_prueba()
