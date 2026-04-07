from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import obtener_sesion
from app.logs import logger
from app.gui import renderizar, obtener_usuario_desde_cookie

router = APIRouter(tags=["GUI"])


@router.get("/")
async def landing(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando página landing")
    usuario = obtener_usuario_desde_cookie(request, sesion)
    return renderizar(request, "landing.html", {"usuario": usuario})


@router.get("/cursos")
@router.get("/cursos/{tipo}")
async def programas(request: Request, tipo: str = None, sesion: Session = Depends(obtener_sesion)):
    logger.info(f"Cargando página de programas, tipo: {tipo}")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    from app.servicios import CursoServicio

    servicio = CursoServicio(sesion)

    if tipo:
        cursos = servicio.obtener_cursos_por_tipo(tipo)
        titulo_pagina = tipo.capitalize()
    else:
        cursos = servicio.obtener_todos_los_cursos()
        titulo_pagina = "Todos los Programas"

    tipos_disponibles = ["CURSO", "DIPLOMADO", "ESPECIALIDAD"]

    return renderizar(
        request,
        "programas.html",
        {
            "usuario": usuario,
            "cursos": cursos,
            "tipo_seleccionado": tipo,
            "titulo_pagina": titulo_pagina,
            "tipos_disponibles": tipos_disponibles,
        },
    )


@router.get("/login")
async def login(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando página login")
    usuario = obtener_usuario_desde_cookie(request, sesion)
    if usuario:
        return RedirectResponse(url="/dashboard", status_code=303)
    return renderizar(request, "login.html", {"usuario": None})


@router.get("/dashboard")
async def dashboard(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando dashboard del usuario")
    usuario = obtener_usuario_desde_cookie(request, sesion)
    if not usuario:
        return RedirectResponse(url="/login", status_code=303)

    from app.servicios import CursoServicio

    servicio = CursoServicio(sesion)
    cursos = servicio.obtener_todos_los_cursos()

    return renderizar(
        request,
        "dashboard.html",
        {
            "usuario": usuario,
            "cursos": cursos,
        },
    )


@router.get("/curso/{slug}")
async def pagina_curso(slug: str, request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info(f"Cargando página del curso: {slug}")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    from app.servicios import CursoServicio

    servicio = CursoServicio(sesion)
    curso = servicio.obtener_curso_por_slug(slug)

    if not curso:
        return renderizar(
            request,
            "error.html",
            {"usuario": usuario, "codigo": 404, "mensaje": "Curso no encontrado"},
        )

    tiene_acceso = False
    if usuario:
        tiene_acceso = servicio.verificar_acceso_curso(usuario.id, curso.id)

    return renderizar(
        request,
        "curso.html",
        {
            "usuario": usuario,
            "curso": curso,
            "tiene_acceso": tiene_acceso,
        },
    )


@router.get("/aula/{slug}")
async def aula(slug: str, request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info(f"Cargando aula virtual: {slug}")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario:
        return RedirectResponse(url="/login", status_code=303)

    from app.servicios import CursoServicio

    servicio = CursoServicio(sesion)
    curso = servicio.obtener_curso_por_slug(slug)

    if not curso:
        return renderizar(
            request,
            "error.html",
            {"usuario": usuario, "codigo": 404, "mensaje": "Curso no encontrado"},
        )

    tiene_acceso = servicio.verificar_acceso_curso(usuario.id, curso.id)
    if not tiene_acceso:
        return RedirectResponse(url=f"/curso/{slug}", status_code=303)

    modulos = servicio.obtener_modulos_y_lecciones(curso.id)

    return renderizar(
        request,
        "aula.html",
        {
            "usuario": usuario,
            "curso": curso,
            "modulos": modulos,
        },
    )


@router.get("/aula/{slug}/leccion/{leccion_id}")
async def cargar_leccion(
    slug: str, leccion_id: int, request: Request, sesion: Session = Depends(obtener_sesion)
):
    logger.info(f"Cargando lección {leccion_id} del curso {slug}")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario:
        return RedirectResponse(url="/login", status_code=303)

    from app.servicios import CursoServicio
    from app.repositorios import CursoRepositorio

    curso_repo = CursoRepositorio(sesion)
    leccion = curso_repo.buscar_leccion_por_id(leccion_id)

    if not leccion:
        return renderizar(
            request,
            "error.html",
            {"usuario": usuario, "codigo": 404, "mensaje": "Lección no encontrada"},
        )

    return renderizar(
        request,
        "leccion_contenido.html",
        {
            "usuario": usuario,
            "leccion": leccion,
        },
    )


@router.get("/foro/{slug}")
async def pagina_foro(slug: str, request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info(f"Cargando foro del curso: {slug}")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario:
        return RedirectResponse(url="/login", status_code=303)

    from app.servicios import CursoServicio, ForoServicio

    curso_servicio = CursoServicio(sesion)
    curso = curso_servicio.obtener_curso_por_slug(slug)

    if not curso:
        return renderizar(
            request,
            "error.html",
            {"usuario": usuario, "codigo": 404, "mensaje": "Curso no encontrado"},
        )

    foro_servicio = ForoServicio(sesion)
    temas = foro_servicio.obtener_temas_curso(curso.id)

    return renderizar(
        request,
        "foro.html",
        {
            "usuario": usuario,
            "curso": curso,
            "temas": temas,
        },
    )


@router.get("/pago/exitoso")
async def pago_exitoso(
    request: Request, session_id: str, sesion: Session = Depends(obtener_sesion)
):
    logger.info(f"Procesando pago exitoso: {session_id}")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario:
        return RedirectResponse(url="/login", status_code=303)

    from app.servicios import CursoServicio
    from app.config import obtener_configuracion

    config = obtener_configuracion()

    return renderizar(
        request,
        "pago_exitoso.html",
        {
            "usuario": usuario,
            "session_id": session_id,
        },
    )


@router.get("/profesorado")
async def profesorado(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando página de profesorado")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    from app.servicios import InstructorServicio, CursoServicio

    instructor_servicio = InstructorServicio(sesion)
    curso_servicio = CursoServicio(sesion)

    instructores = instructor_servicio.obtener_todos()

    instructores_con_cursos = []
    for instructor in instructores:
        cursos = instructor_servicio.obtener_cursos_instructor(instructor.id)
        cursos_detalles = []
        for c in cursos:
            curso = curso_servicio.obtener_curso_por_id(c.curso_id)
            if curso:
                cursos_detalles.append(curso)
        instructores_con_cursos.append({"instructor": instructor, "cursos": cursos_detalles})

    return renderizar(
        request,
        "profesorado.html",
        {
            "usuario": usuario,
            "instructores": instructores_con_cursos,
        },
    )


@router.get("/faq")
async def faq(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando página de FAQ")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    from app.servicios import FaqServicio

    faq_servicio = FaqServicio(sesion)
    faqs = faq_servicio.obtener_todos()

    return renderizar(
        request,
        "faq.html",
        {
            "usuario": usuario,
            "faqs": faqs,
        },
    )


@router.get("/admision")
async def admision(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando página de admisión")
    usuario = obtener_usuario_desde_cookie(request, sesion)
    return renderizar(request, "admision.html", {"usuario": usuario})


@router.get("/contacto")
async def contacto(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando página de contacto")
    usuario = obtener_usuario_desde_cookie(request, sesion)
    return renderizar(request, "contacto.html", {"usuario": usuario})


@router.get("/privacidad")
async def privacidad(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando página de privacidad")
    usuario = obtener_usuario_desde_cookie(request, sesion)
    return renderizar(request, "privacidad.html", {"usuario": usuario})


@router.get("/admin/dashboard")
async def admin_dashboard(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando dashboard admin")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario or usuario.rol.value != "ADMIN":
        return RedirectResponse(url="/login", status_code=303)

    from app.modelos import Usuario, Curso, RolUsuario

    total_usuarios = sesion.query(Usuario).count()
    total_profesores = sesion.query(Usuario).filter(Usuario.rol == RolUsuario.PROFESOR).count()
    total_alumnos = sesion.query(Usuario).filter(Usuario.rol == RolUsuario.ALUMNO).count()
    total_cursos = sesion.query(Curso).count()

    return renderizar(
        request,
        "admin/dashboard.html",
        {
            "usuario": usuario,
            "estadisticas": {
                "total_usuarios": total_usuarios,
                "total_profesores": total_profesores,
                "total_alumnos": total_alumnos,
                "total_cursos": total_cursos,
            },
        },
    )


@router.get("/admin/profesores")
async def admin_profesores(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando página de profesores")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario or usuario.rol.value != "ADMIN":
        return RedirectResponse(url="/login", status_code=303)

    from app.modelos import Usuario, RolUsuario

    profesores = sesion.query(Usuario).filter(Usuario.rol == RolUsuario.PROFESOR).all()

    return renderizar(
        request,
        "admin/profesores.html",
        {
            "usuario": usuario,
            "profesores": profesores,
        },
    )


@router.get("/profesor/dashboard")
async def profesor_dashboard(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando dashboard profesor")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario or usuario.rol.value not in ["ADMIN", "PROFESOR"]:
        return RedirectResponse(url="/login", status_code=303)

    from app.modelos import Curso, CursoInstructor

    instructor_cursos = (
        sesion.query(Curso)
        .join(CursoInstructor)
        .filter(CursoInstructor.usuario_id == usuario.id)
        .all()
    )

    return renderizar(
        request,
        "profesor/dashboard.html",
        {
            "usuario": usuario,
            "mis_cursos": instructor_cursos,
        },
    )


@router.get("/profesor/curso/{curso_id}")
async def profesor_editar_curso(
    curso_id: int, request: Request, sesion: Session = Depends(obtener_sesion)
):
    logger.info(f"Cargando editor de curso {curso_id}")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario or usuario.rol.value not in ["ADMIN", "PROFESOR"]:
        return RedirectResponse(url="/login", status_code=303)

    from app.modelos import Curso, Modulo, Leccion, CursoInstructor

    es_propietario = (
        sesion.query(CursoInstructor)
        .filter(CursoInstructor.curso_id == curso_id, CursoInstructor.usuario_id == usuario.id)
        .first()
    )

    if not es_propietario and usuario.rol.value != "ADMIN":
        return RedirectResponse(url="/profesor/dashboard", status_code=303)

    curso = sesion.query(Curso).filter(Curso.id == curso_id).first()
    modulos = sesion.query(Modulo).filter(Modulo.curso_id == curso_id).order_by(Modulo.orden).all()

    return renderizar(
        request,
        "profesor/editar_curso.html",
        {
            "usuario": usuario,
            "curso": curso,
            "modulos": modulos,
        },
    )
