"""
Bitácoras, vistas
"""
from flask import Blueprint, render_template
from flask_login import login_required
from plataforma_web.blueprints.roles.models import Permiso
from plataforma_web.blueprints.usuarios.decorators import permission_required

from plataforma_web.blueprints.bitacoras.models import Bitacora

bitacoras = Blueprint("bitacoras", __name__, template_folder="templates")


@bitacoras.route("/bitacoras")
@login_required
@permission_required(Permiso.VER_CUENTAS)
def list_active():
    """ Listado de bitácoras """
    bitacoras_activas = Bitacora.query.limit(400).all()
    return render_template("bitacoras/list.jinja2", bitacoras=bitacoras_activas)
