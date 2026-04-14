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
    usuario = None
    try:
        usuario = obtener_usuario_desde_cookie(request, sesion)
    except:
        pass

    from app.servicios import CursoServicio

    servicio = CursoServicio(sesion)

    if tipo:
        cursos = servicio.obtener_cursos_por_tipo(tipo.upper())
        titulo_pagina = tipo.capitalize()
    else:
        cursos = servicio.obtener_todos_los_cursos()
        titulo_pagina = "Todos los Programas"

    # Obtener IDs de cursos comprados - solo si es necesario (lazy)
    cursos_comprados_ids = []
    # Solo cargar si el usuario está en la página y es un estudiante

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
            "cursos_comprados_ids": cursos_comprados_ids,
        },
    )


@router.get("/login")
async def login(
    request: Request,
    sesion: Session = Depends(obtener_sesion),
    session_id: str = None,
    pago_exitoso: str = None,
):
    logger.info("Cargando página login")
    usuario = obtener_usuario_desde_cookie(request, sesion)
    if usuario:
        return RedirectResponse(url="/dashboard", status_code=303)

    datos = {"usuario": None}
    if session_id:
        datos["session_id"] = session_id
        if pago_exitoso:
            datos["mensaje"] = "Tu pago fue exitoso. Inicia sesión para activar tu curso."

    return renderizar(request, "login.html", datos)


@router.get("/dashboard")
async def dashboard(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando dashboard del usuario")
    usuario = obtener_usuario_desde_cookie(request, sesion)
    if not usuario:
        return RedirectResponse(url="/login", status_code=303)

    from app.servicios import CursoServicio

    servicio = CursoServicio(sesion)

    # Para ADMIN/COORDINADOR/PROFESOR: todos los cursos
    # Para ALUMNO: todos los cursos (con marca de comprados)
    if usuario.rol.value in ["ADMIN", "COORDINADOR", "PROFESOR"]:
        cursos = servicio.obtener_todos_los_cursos()
        cursos_comprados_ids = []
    else:
        # estudantes ven TODOS os cursos
        cursos = servicio.obtener_todos_los_cursos()
        # obtener IDs de cursos comprados para marcar
        cursos_comprados = servicio.obtener_cursos_comprados(usuario.id)
        cursos_comprados_ids = [c.id for c in cursos_comprados] if cursos_comprados else []

    return renderizar(
        request,
        "dashboard.html",
        {
            "usuario": usuario,
            "cursos": cursos,
            "cursos_comprados_ids": cursos_comprados_ids,
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
    request: Request, session_id: str = "", sesion: Session = Depends(obtener_sesion)
):
    from fastapi.responses import RedirectResponse

    logger.info(f"Procesando pago exitoso: {session_id}")

    from app.servicios import CursoServicio
    from app.config import obtener_configuracion
    import stripe

    config = obtener_configuracion()
    servicio = CursoServicio(sesion)
    stripe.api_key = config.STRIPE_SECRET_KEY

    curso_id = 0
    usuario_id = 0
    mensaje = "Tu pago está siendo procesado"

    try:
        session_obj = stripe.checkout.Session.retrieve(session_id)
        logger.info(f"Stripe session status: {session_obj.payment_status}")

        usuario_actual = None
        try:
            usuario_actual = obtener_usuario_desde_cookie(request, sesion)
        except:
            pass

        logger.info(f"Usuario actual: {usuario_actual}")

        if session_obj.payment_status == "paid":
            metadata = dict(session_obj.metadata) if session_obj.metadata else {}
            curso_id = int(metadata.get("curso_id", 0))

            logger.info(f"Pago completado: curso={curso_id}, metadata={metadata}")

            if usuario_actual and curso_id:
                tiene_acceso = servicio.verificar_acceso_curso(usuario_actual.id, curso_id)
                if not tiene_acceso:
                    servicio.verificar_y_activar_suscripcion(
                        session_id, usuario_actual.id, curso_id
                    )
                    logger.info(
                        f"Suscripción creada: usuario {usuario_actual.id}, curso {curso_id}"
                    )
                    mensaje = "Tu pago ha sido procesado exitosamente"
                    usuario_id = usuario_actual.id
                else:
                    mensaje = "Ya tienes acceso a este curso"
                    usuario_id = usuario_actual.id
            elif not usuario_actual:
                return RedirectResponse(
                    url=f"/login?pago_exitoso=1&session_id={session_id}", status_code=303
                )
        else:
            logger.warning(f"Pago no completado: status={session_obj.payment_status}")
    except Exception as e:
        logger.error(f"Error verificando pago: {e}", exc_info=True)

    usuario = None
    try:
        usuario = obtener_usuario_desde_cookie(request, sesion)
    except:
        pass

    return renderizar(
        request,
        "pago_exitoso.html",
        {
            "usuario": usuario,
            "session_id": session_id,
            "mensaje": mensaje,
            "curso_id": curso_id,
            "usuario_id": usuario_actual.id if usuario_actual else 0,
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
            "pagina_actual": "/admin/dashboard",
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
    logger.info("Cargando página de personal")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario or usuario.rol.value != "ADMIN":
        return RedirectResponse(url="/login", status_code=303)

    from app.modelos import Usuario, RolUsuario

    # Mostrar todos los usuarios que no son ADMIN ni ALUMNO (profesores y coordinadores)
    personal = (
        sesion.query(Usuario)
        .filter(Usuario.rol.in_([RolUsuario.PROFESOR, RolUsuario.COORDINADOR]))
        .all()
    )

    return renderizar(
        request,
        "admin/profesores.html",
        {
            "usuario": usuario,
            "pagina_actual": "/admin/profesores",
            "profesores": personal,
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
    if not curso:
        return RedirectResponse(url="/profesor/dashboard", status_code=303)

    modulos_orm = (
        sesion.query(Modulo).filter(Modulo.curso_id == curso_id).order_by(Modulo.orden).all()
    )
    modulos_data = []
    for m in modulos_orm:
        lecciones = (
            sesion.query(Leccion).filter(Leccion.modulo_id == m.id).order_by(Leccion.orden).all()
        )
        modulos_data.append(
            {
                "id": m.id,
                "titulo": m.titulo,
                "orden": m.orden,
                "lecciones": [
                    {
                        "id": l.id,
                        "titulo": l.titulo,
                        "orden": l.orden,
                        "video_url": l.video_url,
                        "bunny_video_id": l.bunny_video_id,
                        "estado_video": l.estado_video,
                    }
                    for l in lecciones
                ],
            }
        )

    return renderizar(
        request,
        "profesor/editar_curso.html",
        {
            "usuario": usuario,
            "pagina_actual": "/profesor/cursos",
            "curso": {
                "id": curso.id,
                "titulo": curso.titulo,
                "slug": curso.slug,
                "descripcion": curso.descripcion,
            },
            "modulos": modulos_data,
        },
    )


@router.get("/coordinador/dashboard")
async def coordinator_dashboard(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando dashboard coordinador")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario or usuario.rol.value not in ["ADMIN", "COORDINADOR"]:
        return RedirectResponse(url="/login", status_code=303)

    from app.modelos import Usuario, RolUsuario, Curso, Suscripcion

    total_profesores = (
        sesion.query(Usuario)
        .filter(Usuario.rol == RolUsuario.PROFESOR, Usuario.activo == True)
        .count()
    )
    total_alumnos = (
        sesion.query(Usuario)
        .filter(Usuario.rol == RolUsuario.ALUMNO, Usuario.activo == True)
        .count()
    )
    total_cursos = sesion.query(Curso).count()
    cursos_activos = sesion.query(Curso).filter(Curso.activo == True).count()

    return renderizar(
        request,
        "coordinador/dashboard.html",
        {
            "usuario": usuario,
            "estadisticas": {
                "total_profesores": total_profesores,
                "total_alumnos": total_alumnos,
                "total_cursos": total_cursos,
                "cursos_activos": cursos_activos,
            },
        },
    )


@router.get("/coordinador/profesores")
async def coordinator_profesores(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando página de profesores del coordinador")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario or usuario.rol.value not in ["ADMIN", "COORDINADOR"]:
        return RedirectResponse(url="/login", status_code=303)

    from app.modelos import Usuario, RolUsuario

    profesores = sesion.query(Usuario).filter(Usuario.rol == RolUsuario.PROFESOR).all()

    return renderizar(
        request,
        "coordinador/profesores.html",
        {
            "usuario": usuario,
            "profesores": profesores,
        },
    )


@router.get("/coordinador/alumnos")
async def coordinator_alumnos(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando página de alumnos del coordinador")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario or usuario.rol.value not in ["ADMIN", "COORDINADOR"]:
        return RedirectResponse(url="/login", status_code=303)

    from app.modelos import Usuario, RolUsuario, Suscripcion

    alumnos = sesion.query(Usuario).filter(Usuario.rol == RolUsuario.ALUMNO).all()

    resultado = []
    for a in alumnos:
        suscripciones = (
            sesion.query(Suscripcion)
            .filter(Suscripcion.usuario_id == a.id, Suscripcion.estado == "ACTIVO")
            .count()
        )
        resultado.append(
            {
                "id": a.id,
                "email": a.email,
                "nombre": a.nombre,
                "apellido": a.apellido,
                "activo": a.activo,
                "cursos_inscritos": suscripciones,
                "fecha_registro": a.fecha_registro.isoformat() if a.fecha_registro else None,
            }
        )

    return renderizar(
        request,
        "coordinador/alumnos.html",
        {
            "usuario": usuario,
            "alumnos": resultado,
        },
    )


@router.get("/coordinador/cursos")
async def coordinator_cursos(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando página de cursos del coordinador")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario or usuario.rol.value not in ["ADMIN", "COORDINADOR"]:
        return RedirectResponse(url="/login", status_code=303)

    from app.modelos import Curso, Modulo, Leccion, Suscripcion

    cursos = sesion.query(Curso).order_by(Curso.fecha_creacion.desc()).all()

    resultado = []
    for c in cursos:
        modulos_count = sesion.query(Modulo).filter(Modulo.curso_id == c.id).count()
        lecciones_count = sesion.query(Leccion).join(Modulo).filter(Modulo.curso_id == c.id).count()
        alumnos_count = (
            sesion.query(Suscripcion)
            .filter(Suscripcion.curso_id == c.id, Suscripcion.estado == "ACTIVO")
            .count()
        )

        resultado.append(
            {
                "id": c.id,
                "titulo": c.titulo,
                "slug": c.slug,
                "tipo_programa": c.tipo_programa,
                "precio": c.precio,
                "activo": c.activo,
                "modulos": modulos_count,
                "lecciones": lecciones_count,
                "alumnos": alumnos_count,
                "fecha_creacion": c.fecha_creacion.isoformat() if c.fecha_creacion else None,
            }
        )

    return renderizar(
        request,
        "coordinador/cursos.html",
        {
            "usuario": usuario,
            "cursos": resultado,
        },
    )


@router.get("/coordinador/curso/{curso_id}")
async def coordinator_editar_curso(
    curso_id: int, request: Request, sesion: Session = Depends(obtener_sesion)
):
    logger.info(f"Cargando editor de curso {curso_id} - coordinador")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario or usuario.rol.value not in ["ADMIN", "COORDINADOR"]:
        return RedirectResponse(url="/login", status_code=303)

    from app.modelos import Curso, Modulo, Leccion

    curso = sesion.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        return RedirectResponse(url="/coordinador/cursos", status_code=303)

    modulos = sesion.query(Modulo).filter(Modulo.curso_id == curso_id).order_by(Modulo.orden).all()
    modulos_data = []
    for m in modulos:
        lecciones = (
            sesion.query(Leccion).filter(Leccion.modulo_id == m.id).order_by(Leccion.orden).all()
        )
        modulos_data.append(
            {
                "id": m.id,
                "titulo": m.titulo,
                "orden": m.orden,
                "lecciones": [
                    {
                        "id": l.id,
                        "titulo": l.titulo,
                        "orden": l.orden,
                        "video_url": l.video_url,
                        "bunny_video_id": l.bunny_video_id,
                        "estado_video": l.estado_video,
                        "tipo_video": l.tipo_video,
                    }
                    for l in lecciones
                ],
            }
        )

    return renderizar(
        request,
        "coordinador/curso_editar.html",
        {
            "usuario": usuario,
            "pagina_actual": "/coordinador/cursos",
            "curso": {
                "id": curso.id,
                "titulo": curso.titulo,
                "slug": curso.slug,
                "descripcion": curso.descripcion,
                "descripcion_larga": curso.descripcion_larga,
                "precio": curso.precio,
                "tipo_programa": curso.tipo_programa,
                "activo": curso.activo,
                "imagen_url": curso.imagen_url,
                "fecha_inicio": curso.fecha_inicio.isoformat() if curso.fecha_inicio else None,
                "fecha_fin_inscripcion": curso.fecha_fin_inscripcion.isoformat()
                if curso.fecha_fin_inscripcion
                else None,
                "estado_inscripcion": curso.estado_inscripcion,
                "modalidad": curso.modalidad,
                "duracion_horas": curso.duracion_horas,
                "capacidad_maxima": curso.capacidad_maxima,
            },
            "modulos": modulos_data,
        },
    )


# ==================== ADMIN - ALUMNOS ====================
@router.get("/admin/alumnos")
async def admin_alumnos(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando página de alumnos - admin")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario or usuario.rol.value != "ADMIN":
        return RedirectResponse(url="/login", status_code=303)

    from app.modelos import Usuario, RolUsuario

    # Obtener todos los alumnos como diccionarios
    alumnos_orm = sesion.query(Usuario).filter(Usuario.rol == RolUsuario.ALUMNO).all()
    lista_alumnos = [
        {"nombre": a.nombre, "apellido": a.apellido, "email": a.email, "activo": bool(a.activo)}
        for a in alumnos_orm
    ]

    return renderizar(
        request,
        "admin/alumnos.html",
        {
            "usuario": usuario,
            "pagina_actual": "/admin/alumnos",
            "lista_alumnos": lista_alumnos,
            "total_alumnos": len(lista_alumnos),
        },
    )


# ==================== ADMIN - PROGRAMAS ====================
@router.get("/admin/programas")
async def admin_programas(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando página de programas - admin")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario or usuario.rol.value != "ADMIN":
        return RedirectResponse(url="/login", status_code=303)

    from app.modelos import Curso, Modulo, Leccion

    cursos_orm = sesion.query(Curso).all()
    lista_cursos = []
    for c in cursos_orm:
        modulos_count = sesion.query(Modulo).filter(Modulo.curso_id == c.id).count()
        lecciones_count = sesion.query(Leccion).join(Modulo).filter(Modulo.curso_id == c.id).count()
        lista_cursos.append(
            {
                "id": c.id,
                "titulo": c.titulo,
                "tipo": c.tipo_programa,
                "descripcion": c.descripcion or "",
                "precio": c.precio,
                "activo": bool(c.activo),
                "modulos": modulos_count,
                "lecciones": lecciones_count,
            }
        )

    return renderizar(
        request,
        "admin/programas.html",
        {
            "usuario": usuario,
            "pagina_actual": "/admin/programas",
            "lista_cursos": lista_cursos,
        },
    )


@router.get("/admin/curso/{curso_id}")
async def admin_editar_curso(
    curso_id: int, request: Request, sesion: Session = Depends(obtener_sesion)
):
    logger.info(f"Cargando editor de curso {curso_id}")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario or usuario.rol.value != "ADMIN":
        return RedirectResponse(url="/login", status_code=303)

    from app.modelos import Curso, Modulo, Leccion, Instructor, CursoInstructor

    curso = sesion.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        return RedirectResponse(url="/admin/programas", status_code=303)

    modulos = sesion.query(Modulo).filter(Modulo.curso_id == curso_id).order_by(Modulo.orden).all()
    modulos_data = []
    for m in modulos:
        lecciones = (
            sesion.query(Leccion).filter(Leccion.modulo_id == m.id).order_by(Leccion.orden).all()
        )
        modulos_data.append(
            {
                "id": m.id,
                "titulo": m.titulo,
                "orden": m.orden,
                "lecciones": [
                    {"id": l.id, "titulo": l.titulo, "orden": l.orden, "video_url": l.video_url}
                    for l in lecciones
                ],
            }
        )

    instructores_curso = (
        sesion.query(CursoInstructor).filter(CursoInstructor.curso_id == curso_id).all()
    )
    instructores_data = []
    for ci in instructores_curso:
        inst = sesion.query(Instructor).filter(Instructor.id == ci.instructor_id).first()
        if inst:
            instructores_data.append(
                {"id": inst.id, "nombre": f"{inst.nombre} {inst.apellido}", "email": inst.email}
            )

    todos_instructores = sesion.query(Instructor).filter(Instructor.activo == True).all()

    return renderizar(
        request,
        "admin/curso_editar.html",
        {
            "usuario": usuario,
            "pagina_actual": "/admin/programas",
            "curso": {
                "id": curso.id,
                "titulo": curso.titulo,
                "slug": curso.slug,
                "descripcion": curso.descripcion,
                "descripcion_larga": curso.descripcion_larga,
                "precio": curso.precio,
                "tipo_programa": curso.tipo_programa,
                "activo": curso.activo,
                "imagen_url": curso.imagen_url,
                "fecha_inicio": curso.fecha_inicio.isoformat() if curso.fecha_inicio else None,
                "fecha_fin_inscripcion": curso.fecha_fin_inscripcion.isoformat()
                if curso.fecha_fin_inscripcion
                else None,
                "estado_inscripcion": curso.estado_inscripcion,
                "whatsapp_contacto": curso.whatsapp_contacto,
                "duracion_horas": curso.duracion_horas,
                "modalidad": curso.modalidad,
                "incluye_diploma": curso.incluye_diploma,
                "incluye_materiales": curso.incluye_materiales,
                "requisitos_admision": curso.requisitos_admision,
                "capacidad_maxima": curso.capacidad_maxima,
            },
            "modulos": modulos_data,
            "instructores": instructores_data,
            "todos_instructores": [
                {"id": u.id, "nombre": f"{u.nombre} {u.apellido}", "email": u.email}
                for u in todos_instructores
            ],
        },
    )


# ==================== ADMIN - SUSCRIPCIONES ====================
@router.get("/admin/suscripciones")
async def admin_suscripciones(request: Request, sesion: Session = Depends(obtener_sesion)):
    logger.info("Cargando página de suscripciones - admin")
    usuario = obtener_usuario_desde_cookie(request, sesion)

    if not usuario or usuario.rol.value != "ADMIN":
        return RedirectResponse(url="/login", status_code=303)

    from app.modelos import Suscripcion, Usuario, Curso

    suscripciones = sesion.query(Suscripcion).order_by(Suscripcion.fecha_creacion.desc()).all()

    # Cargar usuarios y cursos
    usuarios = {u.id: u for u in sesion.query(Usuario).all()}
    cursos = {c.id: c for c in sesion.query(Curso).all()}

    return renderizar(
        request,
        "admin/suscripciones.html",
        {
            "usuario": usuario,
            "pagina_actual": "/admin/suscripciones",
            "suscripciones": suscripciones,
            "usuarios": usuarios,
            "cursos": cursos,
        },
    )
