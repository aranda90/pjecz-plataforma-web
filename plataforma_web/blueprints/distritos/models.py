"""
Distritos, modelos
"""
from plataforma_web.extensions import db
from lib.universal_mixin import UniversalMixin


class Distrito(db.Model, UniversalMixin):
    """ Distrito """

    # Nombre de la tabla
    __tablename__ = 'distritos'

    # Clave primaria
    id = db.Column(db.Integer, primary_key=True)

    # Columnas
    nombre = db.Column(db.String(256), unique=True, nullable=False)

    # Hijos
    autoridades = db.relationship('Autoridad', backref='distrito')

    def __repr__(self):
        """ Representación """
        return f'<Distrito {self.nombre}>'