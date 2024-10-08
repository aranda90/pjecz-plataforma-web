"""
CID Procedimientos, vistas
"""

import json
from datetime import datetime, timezone
from delta import html
from flask import abort, Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_, not_

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_email, safe_string, safe_message

from plataforma_web.blueprints.autoridades.models import Autoridad
from plataforma_web.blueprints.bitacoras.models import Bitacora
from plataforma_web.blueprints.cid_procedimientos.forms import (
    CIDProcedimientoForm,
    CIDProcedimientoEditForm,
    CIDProcedimientoAcceptRejectForm,
    CIDProcedimientoEditAdminForm,
    CIDProcedimientoSearchForm,
    CIDProcedimientoCambiarAreaForm,
    CIDProcedimientosNewReview,
)
from plataforma_web.blueprints.cid_procedimientos.models import CIDProcedimiento
from plataforma_web.blueprints.cid_areas.models import CIDArea
from plataforma_web.blueprints.cid_areas_autoridades.models import CIDAreaAutoridad
from plataforma_web.blueprints.cid_formatos.models import CIDFormato
from plataforma_web.blueprints.distritos.models import Distrito
from plataforma_web.blueprints.modulos.models import Modulo
from plataforma_web.blueprints.permisos.models import Permiso
from plataforma_web.blueprints.roles.models import Rol
from plataforma_web.blueprints.usuarios.decorators import permission_required
from plataforma_web.blueprints.usuarios.models import Usuario
from plataforma_web.blueprints.usuarios_roles.models import UsuarioRol

cid_procedimientos = Blueprint("cid_procedimientos", __name__, template_folder="templates")

MODULO = "CID PROCEDIMIENTOS"

# Roles que deben estar en la base de datos
ROL_ADMINISTRADOR = "ADMINISTRADOR"
ROL_COORDINADOR = "SICGD COORDINADOR"
ROL_DIRECTOR_JEFE = "SICGD DIRECTOR O JEFE"
ROL_DUENO_PROCESO = "SICGD DUENO DE PROCESO"
ROL_INVOLUCRADO = "SICGD INVOLUCRADO"
ROLES_CON_PROCEDIMIENTOS_PROPIOS = (ROL_COORDINADOR, ROL_DIRECTOR_JEFE, ROL_DUENO_PROCESO)
ROLES_NUEVA_REVISION = (ROL_COORDINADOR, ROL_DUENO_PROCESO)


@cid_procedimientos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@cid_procedimientos.route("/cid_procedimientos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Cid Procedimientos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = CIDProcedimiento.query
    # Filtrar
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "cid_procedmiento_id" in request.form:
        try:
            cid_procedimiento_id = int(request.form["cid_procedmiento_id"])
            consulta = consulta.filter(CIDProcedimiento.id == cid_procedimiento_id)
        except ValueError:
            pass
    if "codigo" in request.form:
        consulta = consulta.filter(CIDProcedimiento.codigo.contains(safe_clave(request.form["codigo"])))
    if "seguimiento" in request.form:
        consulta = consulta.filter(CIDProcedimiento.seguimiento == request.form["seguimiento"])
    if "titulo_procedimiento" in request.form:
        consulta = consulta.filter(CIDProcedimiento.titulo_procedimiento.contains(safe_string(request.form["titulo_procedimiento"])))
    if "usuario_id" in request.form:
        consulta = consulta.filter(CIDProcedimiento.usuario_id == request.form["usuario_id"])
    if "seguimiento_posterior" in request.form:
        consulta = consulta.filter(CIDProcedimiento.seguimiento_posterior != request.form["seguimiento_posterior"])
    # if "seguimiento_filtro" in request.form:
    #     consulta = consulta.filter(CIDProcedimiento.seguimiento.contains(request.form["seguimiento_filtro"]))
    # if "fecha_desde" in request.form:
    #     consulta = consulta.filter(CIDProcedimiento.creado >= request.form["fecha_desde"])
    # if "fecha_hasta" in request.form:
    #     consulta = consulta.filter(CIDProcedimiento.creado <= request.form["fecha_hasta"])
    # if "elaboro_nombre" in request.form:
    #     consulta = consulta.filter(CIDProcedimiento.elaboro_nombre.contains(safe_string(request.form["elaboro_nombre"])))
    # Si viene el filtro con un listado de ids de areas, filtrar por ellas
    if "cid_areas[]" in request.form:
        areas_a_filtrar = request.form.getlist("cid_areas[]")
        listado_areas_ids = [int(area_id) for area_id in areas_a_filtrar]
        consulta = consulta.filter(CIDProcedimiento.cid_area_id.in_(listado_areas_ids))
    # Ordenar y paginar
    registros = consulta.order_by(CIDProcedimiento.titulo_procedimiento).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.codigo,
                    "url": url_for("cid_procedimientos.detail", cid_procedimiento_id=resultado.id),
                },
                "titulo_procedimiento": resultado.titulo_procedimiento,
                "revision": resultado.revision,
                "elaboro_nombre": resultado.elaboro_email,
                "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                "seguimiento": resultado.seguimiento,
                "seguimiento_posterior": resultado.seguimiento_posterior,
                "usuario": {
                    "nombre": resultado.usuario.nombre,
                    "url": url_for("usuarios.detail", usuario_id=resultado.usuario_id) if current_user.can_view("USUARIOS") else "",
                },
                "autoridad": resultado.autoridad.clave,
                "cid_area": {
                    "clave": resultado.cid_area.clave,
                    "url": url_for("cid_areas.detail", cid_area_id=resultado.cid_area_id) if current_user.can_view("CID AREAS") else "",
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


# Datatable admin
@cid_procedimientos.route("/cid_procedimientos/datatable_json_admin", methods=["GET", "POST"])
def datatable_json_admin():
    """DataTable JSON para listado de Cid Procedimientos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = CIDProcedimiento.query
    # Filtrar
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "cid_procedmiento_id" in request.form:
        try:
            cid_procedimiento_id = int(request.form["cid_procedmiento_id"])
            consulta = consulta.filter(CIDProcedimiento.id == cid_procedimiento_id)
        except ValueError:
            pass
    if "codigo" in request.form:
        consulta = consulta.filter(CIDProcedimiento.codigo.contains(safe_clave(request.form["codigo"])))
    if "seguimiento" in request.form:
        consulta = consulta.filter(CIDProcedimiento.seguimiento == request.form["seguimiento"])
    if "titulo_procedimiento" in request.form:
        consulta = consulta.filter(CIDProcedimiento.titulo_procedimiento.contains(safe_string(request.form["titulo_procedimiento"])))
    if "usuario_id" in request.form:
        consulta = consulta.filter(CIDProcedimiento.usuario_id == request.form["usuario_id"])
    if "seguimiento_posterior" in request.form:
        consulta = consulta.filter(CIDProcedimiento.seguimiento_posterior != request.form["seguimiento_posterior"])
    # if "seguimiento_filtro" in request.form:
    #     consulta = consulta.filter(CIDProcedimiento.seguimiento.contains(request.form["seguimiento_filtro"]))
    # if "fecha_desde" in request.form:
    #     consulta = consulta.filter(CIDProcedimiento.creado >= request.form["fecha_desde"])
    # if "fecha_hasta" in request.form:
    #     consulta = consulta.filter(CIDProcedimiento.creado <= request.form["fecha_hasta"])
    # if "elaboro_nombre" in request.form:
    #     consulta = consulta.filter(CIDProcedimiento.elaboro_nombre.contains(safe_string(request.form["elaboro_nombre"])))
    # Si viene el filtro con un listado de ids de areas, filtrar por ellas
    if "cid_areas[]" in request.form:
        areas_a_filtrar = request.form.getlist("cid_areas[]")
        listado_areas_ids = [int(area_id) for area_id in areas_a_filtrar]
        consulta = consulta.filter(CIDProcedimiento.cid_area_id.in_(listado_areas_ids))
    # Ordenar y paginar
    registros = consulta.order_by(CIDProcedimiento.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("cid_procedimientos.detail", cid_procedimiento_id=resultado.id),
                },
                "titulo_procedimiento": resultado.titulo_procedimiento,
                "codigo": resultado.codigo,
                "revision": resultado.revision,
                "elaboro_nombre": resultado.elaboro_email,
                "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                "seguimiento": resultado.seguimiento,
                "seguimiento_posterior": resultado.seguimiento_posterior,
                "usuario": {
                    "nombre": resultado.usuario.nombre,
                    "url": url_for("usuarios.detail", usuario_id=resultado.usuario_id) if current_user.can_view("USUARIOS") else "",
                },
                "autoridad": resultado.autoridad.clave,
                "cid_area": {
                    "clave": resultado.cid_area.clave,
                    "url": url_for("cid_areas.detail", cid_area_id=resultado.cid_area_id) if current_user.can_view("CID AREAS") else "",
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@cid_procedimientos.route("/cid_procedimientos")
def list_active():
    """Listado de procedimientos autorizados de mis áreas"""
    # Consultar las areas del usuario
    cid_areas = CIDArea.query.join(CIDAreaAutoridad).filter(CIDAreaAutoridad.autoridad_id == current_user.autoridad.id).all()
    # Definir listado de ids de areas
    cid_areas_ids = [cid_area.id for cid_area in cid_areas]
    # Si no tiene areas asignadas, redirigir a la lista de procedimientos autorizados
    if len(cid_areas_ids) == 0:
        return redirect(url_for("cid_procedimientos.list_authorized"))
    # Consultar los roles del usuario
    current_user_roles = set(current_user.get_roles())
    # Si es administrador, usar list_admin.jinja2
    if current_user.can_admin(MODULO) and ROL_ADMINISTRADOR in current_user_roles:
        return render_template(
            "cid_procedimientos/list_admin.jinja2",
            titulo="Procedimientos autorizados de mis áreas",
            filtros=json.dumps({"estatus": "A", "seguimiento": "AUTORIZADO", "cid_areas": cid_areas_ids}),
            estatus="A",
            show_button_list_owned=current_user_roles.intersection(ROLES_CON_PROCEDIMIENTOS_PROPIOS),
            show_button_list_all=ROL_COORDINADOR in current_user_roles,
            show_button_list_all_autorized=True,
            show_button_my_autorized=False,
            show_lista_maestra=ROL_COORDINADOR in current_user_roles,
        )
    # De lo contrario, usar list.jinja2
    return render_template(
        "cid_procedimientos/list.jinja2",
        titulo="Procedimientos autorizados de mis áreas",
        filtros=json.dumps({"estatus": "A", "seguimiento": "AUTORIZADO", "cid_areas": cid_areas_ids, "seguimiento_posterior": "ARCHIVADO"}),
        estatus="A",
        show_button_list_owned=current_user_roles.intersection(ROLES_CON_PROCEDIMIENTOS_PROPIOS),
        show_button_list_all=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
        show_button_list_all_autorized=True,
        show_button_my_autorized=False,
        show_lista_maestra=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
    )


@cid_procedimientos.route("/cid_procedimientos/autorizados")
def list_authorized():
    """Listado de todos los procedimientos autorizados"""
    # Consultar los roles del usuario
    current_user_roles = set(current_user.get_roles())
    # Si es administrador, usar list_admin.jinja2
    if current_user.can_admin(MODULO) and ROL_ADMINISTRADOR in current_user_roles:
        return render_template(
            "cid_procedimientos/list_admin.jinja2",
            titulo="Todos los procedimientos autorizados",
            filtros=json.dumps({"estatus": "A", "seguimiento": "AUTORIZADO", "seguimiento_posterior": "ARCHIVADO"}),
            estatus="A",
            show_button_list_owned=current_user_roles.intersection(ROLES_CON_PROCEDIMIENTOS_PROPIOS),
            show_button_list_all=ROL_COORDINADOR in current_user_roles,
            show_button_list_all_autorized=False,
            show_button_my_autorized=True,
            show_lista_maestra=ROL_COORDINADOR in current_user_roles,
        )
    # De lo contrario, usar list.jinja2
    return render_template(
        "cid_procedimientos/list.jinja2",
        titulo="Todos los procedimientos autorizados",
        filtros=json.dumps({"estatus": "A", "seguimiento": "AUTORIZADO", "seguimiento_posterior": "ARCHIVADO"}),
        estatus="A",
        show_button_list_owned=current_user_roles.intersection(ROLES_CON_PROCEDIMIENTOS_PROPIOS),
        show_button_list_all=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
        show_button_list_all_autorized=False,
        show_button_my_autorized=True,
        show_lista_maestra=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
    )


@cid_procedimientos.route("/cid_procedimientos/propios")
def list_owned():
    """Listado de procedimientos propios"""

    # Consultar los roles del usuario
    current_user_roles = set(current_user.get_roles())

    # Si es administrador, usar list_admin.jinja2
    if current_user.can_admin(MODULO) and ROL_ADMINISTRADOR in current_user_roles:
        return render_template(
            "cid_procedimientos/list_admin.jinja2",
            # cid_procedimiento=procedimientos_archivados_list,
            titulo="Procedimientos propios",
            filtros=json.dumps({"estatus": "A", "usuario_id": current_user.id, "seguimiento_posterior": "ARCHIVADO"}),
            estatus="A",
            show_button_list_owned=False,
            show_button_list_all=ROL_COORDINADOR in current_user_roles,
            show_button_list_all_autorized=True,
            show_button_my_autorized=True,
            show_lista_maestra=ROL_COORDINADOR in current_user_roles,
        )
    # De lo contrario, usar list.jinja2
    return render_template(
        "cid_procedimientos/list.jinja2",
        # cid_procedimiento=procedimientos_archivados_list,
        titulo="Procedimientos propios",
        filtros=json.dumps({"estatus": "A", "usuario_id": current_user.id, "seguimiento_posterior": "ARCHIVADO"}),
        estatus="A",
        show_button_list_owned=False,
        show_button_list_all=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
        show_button_list_all_autorized=True,
        show_button_my_autorized=True,
        show_lista_maestra=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
    )


@cid_procedimientos.route("/cid_procedimientos/activos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_all_active():
    """Listado de procedimientos activos, solo para administrador"""
    # Consultar los roles del usuario
    current_user_roles = set(current_user.get_roles())
    # Si es administrador, usar list_admin.jinja2
    if current_user.can_admin(MODULO) and ROL_ADMINISTRADOR in current_user_roles:
        return render_template(
            "cid_procedimientos/list_admin.jinja2",
            titulo="Todos los procedimientos activos",
            filtros=json.dumps({"estatus": "A"}),
            estatus="A",
            show_button_list_owned=True,
            show_button_list_all=False,
            show_button_list_all_autorized=True,
            show_button_my_autorized=True,
            show_lista_maestra=True,
        )
    return render_template(
        "cid_procedimientos/list.jinja2",
        titulo="Todos los procedimientos activos",
        filtros=json.dumps({"estatus": "A"}),
        estatus="A",
        show_button_list_owned=True,
        show_button_list_all=False,
        show_button_list_all_autorized=True,
        show_button_my_autorized=True,
        show_lista_maestra=True,
    )


@cid_procedimientos.route("/cid_procedimientos/eliminados")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_all_inactive():
    """Listado de procedimientos eliminados, solo para administrador"""
    # Consultar los roles del usuario
    current_user_roles = set(current_user.get_roles())
    return render_template(
        "cid_procedimientos/list_admin.jinja2",
        titulo="Todos los procedimientos eliminados",
        filtros=json.dumps({"estatus": "B"}),
        estatus="B",
        show_button_list_owned=True,
        show_button_list_all=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
        show_button_list_all_autorized=True,
        show_button_my_autorized=True,
        show_lista_maestra=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles,
    )


@cid_procedimientos.route("/cid_procedimientos/<int:cid_procedimiento_id>")
def detail(cid_procedimiento_id):
    """Detalle de un CID Procedimiento"""
    # Consultar los roles del usuario
    current_user_roles = set(current_user.get_roles())
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    cid_formatos = CIDFormato.query.filter(CIDFormato.procedimiento == cid_procedimiento).filter(CIDFormato.estatus == "A").order_by(CIDFormato.id).all()
    # Habilitar o deshabilitar poder cambiar área
    show_cambiar_area = (current_user.id == cid_procedimiento.usuario_id) or (ROL_COORDINADOR in current_user_roles)

    return render_template(
        "cid_procedimientos/detail.jinja2",
        cid_procedimiento=cid_procedimiento,
        firma_al_vuelo=cid_procedimiento.elaborar_firma(),
        objetivo=str(html.render(cid_procedimiento.objetivo["ops"])),
        alcance=str(html.render(cid_procedimiento.alcance["ops"])),
        documentos=str(html.render(cid_procedimiento.documentos["ops"])),
        definiciones=str(html.render(cid_procedimiento.definiciones["ops"])),
        responsabilidades=str(html.render(cid_procedimiento.responsabilidades["ops"])),
        desarrollo=str(html.render(cid_procedimiento.desarrollo["ops"])),
        registros=cid_procedimiento.registros,
        control_cambios=cid_procedimiento.control_cambios,
        cid_formatos=cid_formatos,
        show_button_edit_admin=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user.get_roles(),
        show_cambiar_area=show_cambiar_area,
        show_buttom_new_revision=current_user_roles.intersection(ROLES_NUEVA_REVISION),
    )


@cid_procedimientos.route("/cid_procedimientos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo CID Procedimiento"""
    form = CIDProcedimientoForm()
    if form.validate_on_submit():
        # Obtener la autoridad del usuario actual
        autoridad = current_user.autoridad
        # Consultar la tablaCIDAreaAutoridad para obtener las relación entre la autoridad y el área correspondiente
        area_autoridad = CIDAreaAutoridad.query.filter_by(autoridad_id=autoridad.id).first()
        # Verificar si se encontró un registro válido en la tabla CIDAreaAutoridad y si el área relacionada está definida
        if not area_autoridad or not area_autoridad.cid_area:
            # Mostrar un mensaje de error si no se encontró un área asociada a la autoridad del usuario
            flash("No se encontró un área asociada a la autoridad del usuario.", "error")
            # Redirigir al usuario a la página para crear un nuevo procedimiento
            return redirect(url_for("cid_procedimientos.new"))
        area = area_autoridad.cid_area  # Obtener el área relacionada
        elaboro = form.elaboro_email.data
        if elaboro is None:
            elaboro_nombre = ""
            elaboro_email = ""
        else:
            elaboro_nombre = form.elaboro_nombre.data
            elaboro_email = elaboro
        reviso = form.reviso_email.data
        if reviso is None:
            reviso_nombre = ""
            reviso_email = ""
        else:
            reviso_nombre = form.reviso_nombre.data
            reviso_email = reviso
        aprobo = form.aprobo_email.data
        if aprobo is None:
            aprobo_nombre = ""
            aprobo_email = ""
        else:
            aprobo_nombre = form.aprobo_nombre.data
            aprobo_email = aprobo
        registros_data = form.registros.data
        if registros_data is None:
            registros = {}
        else:
            registros = registros_data
        control = form.control_cambios.data
        if control is None:
            control_cambios = {}
        else:
            control_cambios = control
        cid_procedimiento = CIDProcedimiento(
            autoridad=current_user.autoridad,
            usuario=current_user,
            titulo_procedimiento=safe_string(form.titulo_procedimiento.data),
            codigo=safe_clave(form.codigo.data),
            revision=form.revision.data,
            fecha=form.fecha.data,
            objetivo=form.objetivo.data,
            alcance=form.alcance.data,
            documentos=form.documentos.data,
            definiciones=form.definiciones.data,
            responsabilidades=form.responsabilidades.data,
            desarrollo=form.desarrollo.data,
            registros=registros,
            elaboro_nombre=safe_string(elaboro_nombre, save_enie=True),
            elaboro_puesto=safe_string(form.elaboro_puesto.data),
            elaboro_email=safe_email(elaboro_email),
            reviso_nombre=safe_string(reviso_nombre, save_enie=True),
            reviso_puesto=safe_string(form.reviso_puesto.data),
            reviso_email=safe_email(reviso_email),
            aprobo_nombre=safe_string(aprobo_nombre, save_enie=True),
            aprobo_puesto=safe_string(form.aprobo_puesto.data),
            aprobo_email=safe_email(aprobo_email),
            control_cambios=control_cambios,
            cadena=0,
            seguimiento="EN ELABORACION",
            seguimiento_posterior="EN ELABORACION",
            anterior_id=0,
            firma="",
            archivo="",
            url="",
            cid_area_id=area.id,  # Asignar el área obtenida
        )
        cid_procedimiento.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Procedimiento {cid_procedimiento.titulo_procedimiento}"),
            url=url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("cid_procedimientos/new.jinja2", form=form, help_quill=help_quill("new"))


@cid_procedimientos.route("/cid_procedimientos/edicion/<int:cid_procedimiento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(cid_procedimiento_id):
    """Editar CID Procedimiento"""
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    if not (current_user.can_admin(MODULO) or cid_procedimiento.usuario_id == current_user.id):
        abort(403)  # Acceso no autorizado, solo administradores o el propietario puede editarlo
    if cid_procedimiento.seguimiento not in ["EN ELABORACION", "EN REVISION", "EN AUTORIZACION"]:
        flash(f"No puede editar porque su seguimiento es {cid_procedimiento.seguimiento} y ha sido FIRMADO. ", "warning")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento_id))
    form = CIDProcedimientoEditForm()
    if form.validate_on_submit():
        elaboro = form.elaboro_email.data
        if elaboro is None or elaboro == "":
            elaboro_nombre = ""
            elaboro_email = ""
        else:
            elaboro_nombre = form.elaboro_nombre.data
            elaboro_email = elaboro
        reviso = form.reviso_email.data
        if reviso is None or reviso == "":
            reviso_nombre = ""
            reviso_email = ""
        else:
            reviso_nombre = form.reviso_nombre.data
            reviso_email = reviso
        aprobo = form.aprobo_email.data
        if aprobo is None or aprobo == "":
            aprobo_nombre = ""
            aprobo_email = ""
        else:
            aprobo_nombre = form.aprobo_nombre.data
            aprobo_email = aprobo
        registro = form.registros.data
        if registro is None:
            registros = {}
        else:
            registros = registro
        control = form.control_cambios.data
        if control is None:
            control_cambios = {}
        else:
            control_cambios = control
        # Si el campo revision está vacío o es None, asignar un valor predeterminado
        revision = form.revision.data
        if revision is None:
            revision = 1
        # Asegurar que el campo codigo tenga un valor válido
        codigo = form.codigo.data
        if not codigo:  # Verificar si es None o una cadena vacía
            codigo = cid_procedimiento.codigo  # Mantener el valor original si no se envió uno nuevo
        cid_procedimiento.titulo_procedimiento = safe_string(form.titulo_procedimiento.data)
        cid_procedimiento.codigo = safe_clave(codigo)
        cid_procedimiento.revision = revision
        cid_procedimiento.fecha = form.fecha.data
        cid_procedimiento.objetivo = form.objetivo.data
        cid_procedimiento.alcance = form.alcance.data
        cid_procedimiento.documentos = form.documentos.data
        cid_procedimiento.definiciones = form.definiciones.data
        cid_procedimiento.responsabilidades = form.responsabilidades.data
        cid_procedimiento.desarrollo = form.desarrollo.data
        cid_procedimiento.registros = registros
        cid_procedimiento.elaboro_nombre = safe_string(elaboro_nombre, save_enie=True)
        cid_procedimiento.elaboro_puesto = safe_string(form.elaboro_puesto.data)
        cid_procedimiento.elaboro_email = safe_email(elaboro_email)
        cid_procedimiento.reviso_nombre = safe_string(reviso_nombre, save_enie=True)
        cid_procedimiento.reviso_puesto = safe_string(form.reviso_puesto.data)
        cid_procedimiento.reviso_email = safe_email(reviso_email)
        cid_procedimiento.aprobo_nombre = safe_string(aprobo_nombre, save_enie=True)
        cid_procedimiento.aprobo_puesto = safe_string(form.aprobo_puesto.data)
        cid_procedimiento.aprobo_email = safe_email(aprobo_email)
        cid_procedimiento.control_cambios = control_cambios
        cid_procedimiento.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Procedimiento {cid_procedimiento.titulo_procedimiento}."),
            url=url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Definir los valores de los campos del formulario
    form.titulo_procedimiento.data = cid_procedimiento.titulo_procedimiento
    form.codigo.data = cid_procedimiento.codigo
    form.revision.data = cid_procedimiento.revision
    form.cid_area.data = cid_procedimiento.cid_area
    form.fecha.data = cid_procedimiento.fecha
    form.objetivo.data = cid_procedimiento.objetivo
    form.alcance.data = cid_procedimiento.alcance
    form.documentos.data = cid_procedimiento.documentos
    form.definiciones.data = cid_procedimiento.definiciones
    form.responsabilidades.data = cid_procedimiento.responsabilidades
    form.desarrollo.data = cid_procedimiento.desarrollo
    form.registros.data = cid_procedimiento.registros
    form.elaboro_nombre.data = cid_procedimiento.elaboro_nombre
    form.elaboro_puesto.data = cid_procedimiento.elaboro_puesto
    form.elaboro_email.data = cid_procedimiento.elaboro_email
    form.reviso_nombre.data = cid_procedimiento.reviso_nombre
    form.reviso_puesto.data = cid_procedimiento.reviso_puesto
    form.reviso_email.data = cid_procedimiento.reviso_email
    form.aprobo_nombre.data = cid_procedimiento.aprobo_nombre
    form.aprobo_puesto.data = cid_procedimiento.aprobo_puesto
    form.aprobo_email.data = cid_procedimiento.aprobo_email
    form.control_cambios.data = cid_procedimiento.control_cambios
    # Para cargar el contenido de los QuillJS hay que convertir a JSON válido (por ejemplo, cambia True por true)
    objetivo_json = json.dumps(cid_procedimiento.objetivo)
    alcance_json = json.dumps(cid_procedimiento.alcance)
    documentos_json = json.dumps(cid_procedimiento.documentos)
    definiciones_json = json.dumps(cid_procedimiento.definiciones)
    responsabilidades_json = json.dumps(cid_procedimiento.responsabilidades)
    desarrollo_json = json.dumps(cid_procedimiento.desarrollo)
    registros_json = json.dumps(cid_procedimiento.registros)
    control_cambios_json = json.dumps(cid_procedimiento.control_cambios)
    return render_template(
        "cid_procedimientos/edit.jinja2",
        form=form,
        cid_procedimiento=cid_procedimiento,
        objetivo_json=objetivo_json,
        alcance_json=alcance_json,
        documentos_json=documentos_json,
        definiciones_json=definiciones_json,
        responsabilidades_json=responsabilidades_json,
        desarrollo_json=desarrollo_json,
        registros_json=registros_json,
        control_cambios_json=control_cambios_json,
        help_quill=help_quill("edit"),
    )


# Cambiar la Autoridad al procedimiento
@cid_procedimientos.route("/cid_procedimientos/modificar/<int:cid_procedimiento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit_admin(cid_procedimiento_id):
    """Modificar Autoridad Procedimiento"""
    # Consultar los roles del usuario
    current_user_roles = current_user.get_roles()
    # Si NO es administrador o coordinador, redirigir a la edicion normal
    if not (current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user_roles):
        return redirect(url_for("cid_procedimientos.edit", cid_procedimiento_id=cid_procedimiento_id))
    # Consultar el Procedimiento
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    # Si viene el formulario
    form = CIDProcedimientoEditAdminForm()
    if form.validate_on_submit():
        autoridad = Autoridad.query.get_or_404(form.autoridad.data)
        cid_procedimiento.autoridad = autoridad
        cid_procedimiento.save()
        # Registrar en la bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Modificada la Autoridad del Procedimiento {cid_procedimiento.id}"),
            url=url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Mostrar el formulario
    distritos = Distrito.query.filter_by(estatus="A").order_by(Distrito.nombre).all()  # Combo distritos-autoridades
    autoridades = Autoridad.query.filter_by(estatus="A").order_by(Autoridad.clave).all()  # Combo distritos-autoridades
    form.titulo_procedimiento.data = cid_procedimiento.titulo_procedimiento
    return render_template(
        "cid_procedimientos/edit_admin.jinja2",
        form=form,
        cid_procedimiento=cid_procedimiento,
        distritos=distritos,
        autoridades=autoridades,
    )


# Cambiar el Área del procedimiento
@cid_procedimientos.route("/cid_procedimientos/cambiar_area/<int:cid_procedimiento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def cambiar_area(cid_procedimiento_id):
    """Cambiar Área Procedimiento"""
    # Consultar el procedimiento
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    form = CIDProcedimientoCambiarAreaForm()
    if form.validate_on_submit():
        cid_procedimiento.cid_area = form.cid_area.data
        cid_procedimiento.save()
        # Registrar en bitacora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Cambiada el Área del Procedimiento {cid_procedimiento_id}."),
            url=url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Mostrar
    form.titulo_procedimiento.data = cid_procedimiento.titulo_procedimiento
    form.codigo.data = cid_procedimiento.codigo
    form.cid_area_original.data = cid_procedimiento.cid_area.nombre
    form.cid_area.data = cid_procedimiento.cid_area
    return render_template("cid_procedimientos/cambiar_area.jinja2", form=form, cid_procedimiento=cid_procedimiento)


def validate_json_quill_not_empty(data):
    """Validar que un JSON de Quill no esté vacío"""
    if not isinstance(data, dict):
        return False
    if not "ops" in data:
        return False
    try:
        if data["ops"][0]["insert"].strip() == "":
            return False
        return True
    except KeyError:
        return False


@cid_procedimientos.route("/cid_procedimientos/firmar/<int:cid_procedimiento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def sign_for_maker(cid_procedimiento_id):
    """Firmar"""
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    if cid_procedimiento.usuario_id != current_user.id:
        abort(403)  # Acceso no autorizado, solo el propietario puede firmarlo
    # Validar objetivo
    objetivo_es_valido = validate_json_quill_not_empty(cid_procedimiento.objetivo)
    # Validar alcance
    alcance_es_valido = validate_json_quill_not_empty(cid_procedimiento.alcance)
    # Validar documentos
    documentos_es_valido = validate_json_quill_not_empty(cid_procedimiento.documentos)
    # Validar definiciones
    definiciones_es_valido = validate_json_quill_not_empty(cid_procedimiento.definiciones)
    # Validar responsabilidades
    responsabilidades_es_valido = validate_json_quill_not_empty(cid_procedimiento.responsabilidades)
    # Validar desarrollo
    desarrollo_es_valido = validate_json_quill_not_empty(cid_procedimiento.desarrollo)
    # Validar registros
    registros_es_valido = cid_procedimiento.registros
    # Validar control_cambios
    control_cambios_es_valido = cid_procedimiento.control_cambios
    # Validar elaboro
    elaboro_es_valido = False
    if cid_procedimiento.elaboro_email != "":
        elaboro = Usuario.query.filter_by(email=cid_procedimiento.elaboro_email).first()
        elaboro_es_valido = elaboro is not None  # TODO: Validar que tenga el rol SICGD DUENO DE PROCESO
    # Validar reviso
    reviso_es_valido = False
    if cid_procedimiento.reviso_email != "":
        reviso = Usuario.query.filter_by(email=cid_procedimiento.reviso_email).first()
        reviso_es_valido = reviso is not None  # TODO: Validar que tenga el rol SICGD DIRECTOR O JEFE
    # Validar autorizo
    aprobo_es_valido = False
    if cid_procedimiento.aprobo_email != "":
        aprobo = Usuario.query.filter_by(email=cid_procedimiento.aprobo_email).first()
        aprobo_es_valido = aprobo is not None  # TODO: Validar que tenga el rol SICGD DIRECTOR O JEFE
    # Poner barreras para prevenir que se firme si está incompleto
    if cid_procedimiento.firma != "":
        flash("Este procedimiento ya ha sido firmado.", "warning")
    elif not objetivo_es_valido:
        flash("Objetivo no pasa la validación.", "warning")
    elif not alcance_es_valido:
        flash("Alcance no pasa la validación.", "warning")
    elif not documentos_es_valido:
        flash("Documentos no pasa la validación.", "warning")
    elif not definiciones_es_valido:
        flash("Definiciones no pasa la validación.", "warning")
    elif not responsabilidades_es_valido:
        flash("Responsabilidades no pasa la validación.", "warning")
    elif not desarrollo_es_valido:
        flash("Desarrollo no pasa la validación.", "warning")
    elif not registros_es_valido:
        flash("Registros no pasa la validación.", "warning")
    elif not control_cambios_es_valido:
        flash("Control de Cambios no pasa la validación.", "warning")
    elif not elaboro_es_valido:
        flash("Quien elabora no pasa la validación.", "warning")
    elif not reviso_es_valido:
        flash("Quien revisa no pasa la validación.", "warning")
    elif not aprobo_es_valido:
        flash("Quien aprueba no pasa la validación.", "warning")
    else:
        tarea = current_user.launch_task(
            comando="cid_procedimientos.tasks.crear_pdf",
            mensaje=f"Se esta creando PDF de {cid_procedimiento.titulo_procedimiento}",
            usuario_id=current_user.id,
            cid_procedimiento_id=cid_procedimiento.id,
            accept_reject_url=url_for("cid_procedimientos.accept_reject", cid_procedimiento_id=cid_procedimiento.id),
        )
        flash(f"{tarea.descripcion} y esta corriendo en el fondo. Esta página se va recargar en 20 segundos...", "info")
    return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id))


@cid_procedimientos.route("/cid_procedimientos/aceptar_rechazar/<int:cid_procedimiento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def accept_reject(cid_procedimiento_id):
    """Aceptar o Rechazar un Procedimiento"""
    original = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    # Validar que NO haya sido eliminado
    if original.estatus != "A":
        flash("Este procedimiento no es activo.", "warning")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
    # Validar que este procedimiento este elaborado o revisado
    if not original.seguimiento in ["ELABORADO", "REVISADO"]:
        flash("Este procedimiento no puede ser aceptado.", "warning")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
    # Validar que NO haya sido YA aceptado
    if original.seguimiento_posterior in ["EN REVISION", "EN AUTORIZACION"]:
        flash("Este procedimiento ya fue aceptado.", "warning")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
    # Validación para procedimientos AUTORIZADO y no poder aceptar de nuevo
    if original.seguimiento == "REVISADO" and original.seguimiento_posterior == "AUTORIZADO":
        flash("Este procedimiento ya ha sido AUTORIZADO y no puede ser aceptado nuevamente.", "warning")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
    form = CIDProcedimientoAcceptRejectForm()
    if form.validate_on_submit():
        # Si fue aceptado
        if form.aceptar.data is True:
            # Deberian definirse estos campos
            nuevo_seguimiento = None
            nuevo_seguimiento_posterior = None
            nuevo_usuario = None
            # Si este procedimiento fue elaborado, sigue revisarlo
            if original.seguimiento == "ELABORADO":
                usuario = Usuario.query.filter_by(email=original.reviso_email).first()
                if usuario is None:
                    flash(f"No fue encontrado el usuario con e-mail {original.reviso_email}", "danger")
                    return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
                nuevo_seguimiento = "EN REVISION"
                nuevo_seguimiento_posterior = "EN REVISION"
                nuevo_usuario = usuario
            # Si este procedimiento fue revisado, sigue autorizarlo
            if original.seguimiento == "REVISADO":
                usuario = Usuario.query.filter_by(email=original.aprobo_email).first()
                if usuario is None:
                    flash(f"No fue encontrado el usuario con e-mail {original.aprobo_email}", "danger")
                    return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
                nuevo_seguimiento = "EN AUTORIZACION"
                nuevo_seguimiento_posterior = "EN AUTORIZACION"
                nuevo_usuario = usuario
            # Validar que se hayan definido estos campos
            if nuevo_seguimiento is None:
                flash("No se definio el seguimiento.", "danger")
                return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
            if nuevo_seguimiento_posterior is None:
                flash("No se definio el seguimiento posterior.", "danger")
                return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
            if nuevo_usuario is None:
                flash("No se definio el usuario.", "danger")
                return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
            # Validar que NO haya sido YA aceptado
            if original.seguimiento_posterior in ["EN REVISION", "EN AUTORIZACION"]:
                flash("Este procedimiento ya fue aceptado.", "warning")
                return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
            # Crear un nuevo registro
            nuevo = CIDProcedimiento(
                autoridad=original.autoridad,
                usuario=nuevo_usuario,
                titulo_procedimiento=safe_string(original.titulo_procedimiento),
                codigo=original.codigo,
                revision=original.revision,
                fecha=original.fecha,
                objetivo=original.objetivo,
                alcance=original.alcance,
                documentos=original.documentos,
                definiciones=original.definiciones,
                responsabilidades=original.responsabilidades,
                desarrollo=original.desarrollo,
                registros=original.registros,
                elaboro_nombre=original.elaboro_nombre,
                elaboro_puesto=original.elaboro_puesto,
                elaboro_email=original.elaboro_email,
                reviso_nombre=original.reviso_nombre,
                reviso_puesto=original.reviso_puesto,
                reviso_email=original.reviso_email,
                aprobo_nombre=original.aprobo_nombre,
                aprobo_puesto=original.aprobo_puesto,
                aprobo_email=original.aprobo_email,
                control_cambios=original.control_cambios,
                seguimiento=nuevo_seguimiento,
                seguimiento_posterior=nuevo_seguimiento_posterior,
                cadena=original.cadena + 1,
                anterior_id=original.id,
                firma="",
                archivo="",
                url="",
                cid_area=original.cid_area,
            ).save()
            # Actualizar el anterior
            if original.seguimiento == "ELABORADO":
                # Cambiar el seguimiento posterior del procedimiento elaborado
                anterior = CIDProcedimiento.query.get(cid_procedimiento_id)
                anterior.seguimiento_posterior = "EN REVISION"
                anterior.save()
            if original.seguimiento == "REVISADO":
                # Cambiar el seguimiento posterior del procedimiento revisado
                anterior = CIDProcedimiento.query.get(cid_procedimiento_id)
                anterior.seguimiento_posterior = "EN AUTORIZACION"
                anterior.save()
            # Duplicar los formatos del procedimiento anterior a éste que es el nuevo
            if original.seguimiento == "ELABORADO" or original.seguimiento == "REVISADO":
                for cid_formato in anterior.formatos:
                    CIDFormato(
                        procedimiento=nuevo,
                        descripcion=cid_formato.descripcion,
                        archivo=cid_formato.archivo,
                        url=cid_formato.url,
                        cid_area=cid_formato.cid_area,
                    ).save()
            # Bitacora
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Aceptado el Procedimiento {nuevo.titulo_procedimiento}."),
                url=url_for("cid_procedimientos.detail", cid_procedimiento_id=nuevo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
        # Fue rechazado
        if form.rechazar.data is True:
            # Preguntar porque fue rechazado
            flash("Usted ha rechazado revisar/autorizar este procedimiento.", "success")
        # Ir al detalle del procedimiento
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
    # Mostrar el formulario
    form.titulo_procedimiento.data = original.titulo_procedimiento
    form.codigo.data = original.codigo
    form.revision.data = original.revision
    form.seguimiento.data = original.seguimiento
    form.seguimiento_posterior.data = original.seguimiento_posterior
    form.elaboro_nombre.data = original.elaboro_nombre
    form.reviso_nombre.data = original.reviso_nombre
    form.url.data = original.url
    return render_template("cid_procedimientos/accept_reject.jinja2", form=form, cid_procedimiento=original)


@cid_procedimientos.route("/cid_procedimientos/eliminar/<int:cid_procedimiento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(cid_procedimiento_id):
    """Eliminar CID Procedimiento"""
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    if not (current_user.can_admin(MODULO) or cid_procedimiento.usuario_id == current_user.id):
        abort(403)  # Acceso no autorizado, solo administradores o el propietario puede eliminarlo
    if not (current_user.can_admin(MODULO) or cid_procedimiento.seguimiento in ["EN ELABORACION", "EN REVISION", "EN AUTORIZACION"]):
        flash(f"No puede eliminarlo porque su seguimiento es {cid_procedimiento.seguimiento}.")
    elif cid_procedimiento.estatus == "A":
        if cid_procedimiento.seguimiento == "EN ELABORACION":
            cid_procedimiento.seguimiento = "CANCELADO POR ELABORADOR"
        elif cid_procedimiento.seguimiento == "EN REVISION":
            cid_procedimiento.seguimiento = "CANCELADO POR REVISOR"
        elif cid_procedimiento.seguimiento == "EN AUTORIZACION":
            cid_procedimiento.seguimiento = "CANCELADO POR AUTORIZADOR"
        cid_procedimiento.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Procedimiento {cid_procedimiento.titulo_procedimiento}."),
            url=url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento_id))


@cid_procedimientos.route("/cid_procedimientos/recuperar/<int:cid_procedimiento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(cid_procedimiento_id):
    """Recuperar CID Procedimiento"""
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    if not (current_user.can_admin(MODULO) or cid_procedimiento.usuario_id == current_user.id):
        abort(403)  # Acceso no autorizado, solo administradores o el propietario puede recuperarlo
    if not (current_user.can_admin(MODULO) or cid_procedimiento.seguimiento in ["CANCELADO POR ELABORADOR", "CANCELADO POR REVISOR", "CANCELADO POR AUTORIZADOR"]):
        flash(f"No puede recuperarlo porque su seguimiento es {cid_procedimiento.seguimiento}.")
    elif cid_procedimiento.estatus == "B":
        if cid_procedimiento.seguimiento == "CANCELADO POR ELABORADOR":
            cid_procedimiento.seguimiento = "EN ELABORACION"
        elif cid_procedimiento.seguimiento == "CANCELADO POR REVISOR":
            cid_procedimiento.seguimiento = "EN REVISION"
        elif cid_procedimiento.seguimiento == "CANCELADO POR AUTORIZADOR":
            cid_procedimiento.seguimiento = "EN AUTORIZACION"
        cid_procedimiento.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Procedimiento {cid_procedimiento.titulo_procedimiento}."),
            url=url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento_id))


def help_quill(seccion: str):
    """Cargar archivo de ayuda"""
    archivo_ayuda = open("plataforma_web/static/json/help/quill_help.json", "r")
    data = json.load(archivo_ayuda)
    archivo_ayuda.close()
    return render_template("quill_help.jinja2", titulo=data["titulo"], descripcion=data["descripcion"], secciones=data["secciones"], seccion_id=seccion)


@cid_procedimientos.route("/cid_procedimientos/copiar_revision/<int:cid_procedimiento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def copiar_procedimiento_con_revision(cid_procedimiento_id):
    """Copiar CID Procedimiento con nueva revisión"""
    # Obtener el CID Procedimiento correspondiente o devolver error 404 si no existe
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    # Verificar que tanto seguimiento como seguimiento_posterior sean AUTORIZADO
    if cid_procedimiento.seguimiento != "AUTORIZADO" or cid_procedimiento.seguimiento_posterior != "AUTORIZADO":
        flash("No se puede copiar el procedimiento hasta que ambos seguimientos estén en 'AUTORIZADO'.", "danger")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id))
    # Obtener la última revisión
    ultima_revision = CIDProcedimiento.query.filter_by(id=cid_procedimiento.id).order_by(CIDProcedimiento.revision.desc()).first()

    # Obtener el número de revisión actual
    numero_revision_actual = cid_procedimiento.revision

    # Crear un formulario para la nueva revisión
    form = CIDProcedimientosNewReview()
    # Si el formulario ha sido enviado y es válido
    if form.validate_on_submit():
        reviso = form.reviso_email.data
        if reviso is None or reviso == "":
            reviso_nombre = ""
            reviso_email = ""
        else:
            reviso_nombre = form.reviso_nombre.data
            reviso_email = reviso
        aprobo = form.aprobo_email.data
        if aprobo is None or aprobo == "":
            aprobo_nombre = ""
            aprobo_email = ""
        else:
            aprobo_nombre = form.aprobo_nombre.data
            aprobo_email = aprobo
        # Acceder a los datos del formulario
        cid_procedimiento.titulo_prcedimiento = safe_string(form.titulo_procedimiento.data)
        cid_procedimiento.codigo = form.codigo.data
        cid_procedimiento.revision = form.revision.data
        cid_procedimiento.fecha = form.fecha.data if form.fecha.data else datetime.now(timezone.utc)
        cid_procedimiento.reviso_nombre = safe_string(reviso_nombre, save_enie=True)
        cid_procedimiento.reviso_puesto = safe_string(form.reviso_puesto.data)
        cid_procedimiento.reviso_email = safe_email(reviso_email)
        cid_procedimiento.aprobo_nombre = safe_string(aprobo_nombre, save_enie=True)
        cid_procedimiento.aprobo_puesto = safe_string(form.aprobo_puesto.data)
        cid_procedimiento.aprobo_email = safe_email(aprobo_email)

        # Crear una nueva copia del procedimiento con los datos actualizados
        nueva_copia = CIDProcedimiento(
            autoridad=cid_procedimiento.autoridad,
            usuario=current_user,
            titulo_procedimiento=safe_string(form.titulo_procedimiento.data),
            codigo=form.codigo.data,
            revision=form.revision.data,
            fecha=form.fecha.data if form.fecha.data else datetime.now(timezone.utc),
            objetivo=cid_procedimiento.objetivo,
            alcance=cid_procedimiento.alcance,
            documentos=cid_procedimiento.documentos,
            definiciones=cid_procedimiento.definiciones,
            responsabilidades=cid_procedimiento.responsabilidades,
            desarrollo=cid_procedimiento.desarrollo,
            registros=cid_procedimiento.registros,
            elaboro_nombre=cid_procedimiento.elaboro_nombre,
            elaboro_puesto=cid_procedimiento.elaboro_puesto,
            elaboro_email=cid_procedimiento.elaboro_email,
            reviso_nombre=cid_procedimiento.reviso_nombre,
            reviso_puesto=cid_procedimiento.reviso_puesto,
            reviso_email=cid_procedimiento.reviso_email,
            aprobo_nombre=cid_procedimiento.aprobo_nombre,
            aprobo_puesto=cid_procedimiento.aprobo_puesto,
            aprobo_email=cid_procedimiento.aprobo_email,
            control_cambios=cid_procedimiento.control_cambios,
            seguimiento="EN ELABORACION",
            seguimiento_posterior="EN ELABORACION",
            cadena=cid_procedimiento.cadena + 1,
            anterior_id=cid_procedimiento.id,
            firma="",
            archivo="",
            url="",
            cid_area=cid_procedimiento.cid_area,
        )
        # Guardar la nueva copia en la base de datos
        nueva_copia.save()
        # Obtener el procedimiento anterior usando su ID, Duplicar los formatos del procedimiento anterior a éste que es el nuevo
        anterior = CIDProcedimiento.query.get(cid_procedimiento_id)
        # Verificar si el seguimiento del nuevo procedimiento es "AUTORIZADO"
        if cid_procedimiento.seguimiento == "AUTORIZADO":
            # Iterar sobre los formatos del procedimiento anterior
            for cid_formato in anterior.formatos:
                # Crear una copia del formato actual y guardarla en la base de datos
                CIDFormato(
                    procedimiento=nueva_copia,  # Establecer el nuevo procedimiento como el procedimiento al que pertenecerá este formato
                    descripcion=cid_formato.descripcion,  # Establecer la descripción del nuevo formato como la misma descripción del formato anterior
                    archivo=cid_formato.archivo,  # Establecer el archivo del nuevo formato como el mismo archivo del formato anterior
                    url=cid_formato.url,  # Establecer la URL del nuevo formato como la misma URL del formato anterior
                    cid_area=cid_formato.cid_area,  # Establecer el área del nuevo formato como la misma área del formato anterior
                ).save()

        # Actualizar el estado de los procedimientos relacionados a "AUTORIZADO"
        relacionados_a_archivar = CIDProcedimiento.query.filter((CIDProcedimiento.codigo == cid_procedimiento.codigo) & ((CIDProcedimiento.seguimiento == "AUTORIZADO") | (CIDProcedimiento.seguimiento_posterior == "AUTORIZADO"))).all()

        for relacionado in relacionados_a_archivar:
            relacionado.seguimiento_posterior = "ARCHIVADO"
            relacionado.revision = numero_revision_actual  # Mantener la revisión del procedimiento anterior
            relacionado.save()

        # Bitácora y redirección a la vista de detalle
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva revisión del procedimiento {cid_procedimiento.titulo_procedimiento}."),
            url=url_for("cid_procedimientos.detail", cid_procedimiento_id=nueva_copia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        # Redireccionar a la edicion del nuevo id
        return redirect(url_for("cid_procedimientos.edit", cid_procedimiento_id=nueva_copia.id))
    # Llenar el formulario con los datos del procedimiento original
    form.titulo_procedimiento.data = cid_procedimiento.titulo_procedimiento
    form.codigo.data = cid_procedimiento.codigo
    form.revision.data = (ultima_revision.revision + 1) if ultima_revision else 1
    form.fecha.data = datetime.now(timezone.utc)
    form.reviso_nombre.data = cid_procedimiento.reviso_nombre
    form.reviso_puesto.data = cid_procedimiento.reviso_puesto
    form.reviso_email.data = cid_procedimiento.reviso_email
    form.aprobo_nombre.data = cid_procedimiento.aprobo_nombre
    form.aprobo_puesto.data = cid_procedimiento.aprobo_puesto
    form.aprobo_email.data = cid_procedimiento.aprobo_email
    # Renderizar la plantilla con el formulario y la información del procedimiento
    return render_template("cid_procedimientos/new_revision.jinja2", form=form, cid_procedimiento=cid_procedimiento)


@cid_procedimientos.route("/cid_procedimientos/usuarios_json", methods=["POST"])
def query_usuarios_json():
    """Proporcionar el JSON de usuarios para elegir con un Select2"""
    usuarios = Usuario.query.filter(Usuario.estatus == "A")
    if "searchString" in request.form:
        usuarios = usuarios.filter(Usuario.email.contains(safe_email(request.form["searchString"], search_fragment=True)))
    results = []
    for usuario in usuarios.order_by(Usuario.email).limit(10).all():
        results.append({"id": usuario.email, "text": usuario.email, "nombre": usuario.nombre})
    return {"results": results, "pagination": {"more": False}}


@cid_procedimientos.route("/cid_procedimientos/revisores_autorizadores_json", methods=["POST"])
def query_revisores_autorizadores_json():
    """Proporcionar el JSON de revisores para elegir con un Select2"""
    usuarios = Usuario.query.join(UsuarioRol, Rol).filter(or_(Rol.nombre == ROL_DIRECTOR_JEFE, Rol.nombre == ROL_COORDINADOR))
    if "searchString" in request.form:
        usuarios = usuarios.filter(Usuario.email.contains(safe_email(request.form["searchString"], search_fragment=True)))
    usuarios = usuarios.filter(Usuario.estatus == "A")
    results = []
    for usuario in usuarios.order_by(Usuario.email).limit(10).all():
        results.append({"id": usuario.email, "text": usuario.email, "nombre": usuario.nombre})
    return {"results": results, "pagination": {"more": False}}


@cid_procedimientos.route("/cid_procedimientos/exportar_lista_maestra_xlsx")
@permission_required(MODULO, Permiso.VER)
def exportar_xlsx():
    """Lanzar tarea en el fondo para exportar la Lista Maestra a un archivo XLSX"""
    tarea = current_user.launch_task(
        comando="cid_procedimientos.tasks.lanzar_exportar_xlsx",
        mensaje="Exportando la Lista Maestra a un archivo XLSX...",
    )
    flash("Se ha lanzado esta tarea en el fondo. Esta página se va a recargar en 30 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))
