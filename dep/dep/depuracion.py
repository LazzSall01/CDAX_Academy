from app.database import SessionLocal
from app.logs import logger
from app.modelos import Usuario, Curso, Modulo, Leccion, Suscripcion, EstadoSuscripcion
from app.modelos import RolUsuario
from datetime import datetime


def crear_datos_ejemplo():
    logger.info("Creando datos de ejemplo para pruebas")
    sesion = SessionLocal()

    try:
        usuario_admin = Usuario(
            google_id="admin_test",
            email="admin@cdaxacademy.com",
            nombre="Admin",
            apellido="Demo",
            rol=RolUsuario.ADMIN,
        )
        sesion.add(usuario_admin)
        sesion.flush()
        logger.info(f"Usuario admin creado: {usuario_admin.email}")

        cursos_data = [
            {
                "titulo": "Flujo Digital en Odontología",
                "descripcion": "Domina el flujo digital completo",
                "precio": 49900,
            },
            {
                "titulo": "IA en Odontología",
                "descripcion": "Inteligencia artificial para diagnóstico",
                "precio": 59900,
            },
            {
                "titulo": "Gestión Financiera Dental",
                "descripcion": "Optimiza tu consultorio",
                "precio": 44900,
            },
        ]

        for i, data in enumerate(cursos_data, 1):
            curso = Curso(
                titulo=data["titulo"],
                slug=f"curso-{i}",
                descripcion=data["descripcion"],
                precio=data["precio"],
                activo=True,
            )
            sesion.add(curso)
            sesion.flush()
            logger.info(f"Curso creado: {curso.titulo}")

            modulo = Modulo(curso_id=curso.id, titulo="Módulo 1: Introducción", orden=1)
            sesion.add(modulo)
            sesion.flush()

            leccion = Leccion(
                modulo_id=modulo.id,
                titulo="Bienvenida al curso",
                descripcion="Introducción y overview del curso",
                video_url="https://www.youtube.com/embed/dQw4w9WgXcQ",
                duracion_minutos=5,
                orden=1,
            )
            sesion.add(leccion)
            logger.info(f"Lección creada: {leccion.titulo}")

        sesion.commit()
        logger.info("Datos de ejemplo creados correctamente")

    except Exception as e:
        logger.error(f"Error al crear datos de ejemplo: {e}")
        sesion.rollback()
    finally:
        sesion.close()


def verificar_base_datos():
    logger.info("Verificando conexión a base de datos")
    sesion = SessionLocal()
    try:
        conteo = sesion.query(Usuario).count()
        logger.info(f"Usuarios en base de datos: {conteo}")
        return conteo
    finally:
        sesion.close()


if __name__ == "__main__":
    verificar_base_datos()
    crear_datos_ejemplo()
