"""
CID Procedimientos, formularios
"""
from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, StringField, SubmitField, SelectField
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import DataRequired, Length, Optional

from lib.wtforms import JSONField
from plataforma_web.blueprints.usuarios.models import Usuario


def usuarios_email_opciones():
    """Seleccionar correo electronico de usuarios: opciones para select"""
    # TODO: Optimizar la consulta de usuarios porque son muchos
    return ""  # Usuario.query.filter_by(estatus="A").order_by(Usuario.email).all()


class CIDProcedimientoForm(FlaskForm):
    """Formulario CID Procedimiento"""

    # Step Encabezado
    titulo_procedimiento = StringField("Título", validators=[DataRequired(), Length(max=256)])
    codigo = StringField("Código", validators=[DataRequired(), Length(max=16)])
    revision = IntegerField("Revisión (Número entero apartir de 1)", validators=[DataRequired()])
    fecha = DateField("Fecha de elaboración", validators=[DataRequired()])
    # Step Objetivo
    objetivo = JSONField("Objetivo", validators=[Optional()])
    # Step Alcance
    alcance = JSONField("Alcance", validators=[Optional()])
    # Step Documentos
    documentos = JSONField("Documentos", validators=[Optional()])
    # Step Definiciones
    definiciones = JSONField("Definiciones", validators=[Optional()])
    # Step Responsabilidades
    responsabilidades = JSONField("Responsabilidades", validators=[Optional()])
    # Step Desarrollo
    desarrollo = JSONField("Desarrollo", validators=[Optional()])
    # Step Registros
    registros = JSONField("Registros", validators=[Optional()])
    # Step Control de Cambios
    control_cambios = JSONField("Control de Cambios", validators=[Optional()])
    # Step Autorizaciones
    elaboro_nombre = StringField("Nombre", validators=[Optional(), Length(max=256)])
    elaboro_puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    elaboro_email = SelectField(label="Correo", coerce=str, validators=[Optional()], validate_choice=False)
    reviso_nombre = StringField("Nombre", validators=[Optional(), Length(max=256)])
    reviso_puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    reviso_email = SelectField(label="Correo", coerce=str, validators=[Optional()], validate_choice=False)
    aprobo_nombre = StringField("Nombre", validators=[Optional(), Length(max=256)])
    aprobo_puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    aprobo_email = SelectField(label="Correo", coerce=str, validators=[Optional()], validate_choice=False)
    autorizaciones = JSONField("Autorizaciones", validators=[Optional()])
    # Guardar
    guardar = SubmitField("Guardar")


class CIDProcedimientoAcceptRejectForm(FlaskForm):
    """Formaulario para Aceptar o Rechazar"""

    titulo_procedimiento = StringField("Título", validators=[DataRequired(), Length(max=256)])
    codigo = StringField("Código", validators=[DataRequired(), Length(max=16)])
    revision = IntegerField("Revisión", validators=[DataRequired()])
    seguimiento = StringField("Seguimiento", validators=[DataRequired()])
    seguimiento_posterior = StringField("Seguimiento posterior", validators=[DataRequired()])
    elaboro_nombre = StringField("Remitente Elaboró", validators=[Optional()])
    reviso_nombre = StringField("Remitente Revisó", validators=[Optional()])
    url = StringField("Archivo PDF", validators=[Optional()])
    aceptar = SubmitField("Aceptar")
    rechazar = SubmitField("Rechazar")


class CIDProcedimientoEditAdminForm(FlaskForm):
    """Formulario CIDProcedimientoAdmin"""

    distrito = SelectField("Distrito", choices=None, validate_choice=False)  # Las opciones se agregan con JS
    autoridad = SelectField("Autoridad", choices=None, validate_choice=False)  # Las opciones se agregan con JS
    titulo_procedimiento = StringField("Título")  # Read only
    codigo = StringField("Código")  # Read only
    revision = IntegerField("Revisión (Número entero apartir de 1)")  # Read only
    guardar = SubmitField("Guardar")
