"""
Abogados, vistas
"""
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required
from plataforma_web.blueprints.roles.models import Permiso
from plataforma_web.blueprints.usuarios.decorators import permission_required

from plataforma_web.blueprints.abogados.models import Abogado
from plataforma_web.blueprints.abogados.forms import AbogadoForm

abogados = Blueprint("abogados", __name__, template_folder="templates")


@abogados.before_request
@login_required
@permission_required(Permiso.VER_CONTENIDOS)
def before_request():
    """ Permiso por defecto """


@abogados.route("/abogados")
def list_active():
    """ Listado de Abogados """
    abogados_activos = Abogado.query.filter(Abogado.estatus == "A").order_by(Abogado.fecha).limit(100).all()
    return render_template("abogados/list.jinja2", abogados=abogados_activos)


@abogados.route("/abogados/<int:abogado_id>")
def detail(abogado_id):
    """ Detalle de un Abogado """
    abogado = Abogado.query.get_or_404(abogado_id)
    return render_template("abogados/detail.jinja2", abogado=abogado)


@abogados.route("/abogados/nuevo", methods=["GET", "POST"])
@permission_required(Permiso.CREAR_CONTENIDOS)
def new():
    """ Nuevo Abogado """
    form = AbogadoForm()
    if form.validate_on_submit():
        abogado = Abogado(
            numero=form.numero.data,
            nombre=form.nombre.data,
            libro=form.libro.data,
            fecha=form.fecha.data,
        )
        abogado.save()
        flash(f"Abogado {abogado.nombre} guardado.", "success")
        return redirect(url_for("abogados.list_active"))
    return render_template("abogados/new.jinja2", form=form)


@abogados.route("/abogados/edicion/<int:abogado_id>", methods=["GET", "POST"])
@permission_required(Permiso.MODIFICAR_CONTENIDOS)
def edit(abogado_id):
    """ Editar Abogado """
    abogado = Abogado.query.get_or_404(abogado_id)
    form = AbogadoForm()
    if form.validate_on_submit():
        abogado.numero = form.numero.data
        abogado.nombre = form.nombre.data
        abogado.libro = form.libro.data
        abogado.fecha = form.fecha.data
        abogado.save()
        flash(f"Abogado {abogado.nombre} guardado.", "success")
        return redirect(url_for("abogados.detail", abogado_id=abogado.id))
    form.numero.data = abogado.numero
    form.nombre.data = abogado.nombre
    form.libro.data = abogado.libro
    form.fecha.data = abogado.fecha
    return render_template("abogados/edit.jinja2", form=form, abogado=abogado)


@abogados.route("/abogados/eliminar/<int:abogado_id>")
@permission_required(Permiso.MODIFICAR_CONTENIDOS)
def delete(abogado_id):
    """ Eliminar Abogado """
    abogado = Abogado.query.get_or_404(abogado_id)
    if abogado.estatus == "A":
        abogado.delete()
        flash(f"Abogado {abogado.nombre} eliminado.", "success")
    return redirect(url_for("abogados.detail", abogado_id=abogado_id))


@abogados.route("/abogados/recuperar/<int:abogado_id>")
@permission_required(Permiso.MODIFICAR_CONTENIDOS)
def recover(abogado_id):
    """ Recuperar Abogado """
    abogado = Abogado.query.get_or_404(abogado_id)
    if abogado.estatus == "B":
        abogado.recover()
        flash(f"Abogado {abogado.nombre} recuperado.", "success")
    return redirect(url_for("abogados.detail", abogado_id=abogado_id))
