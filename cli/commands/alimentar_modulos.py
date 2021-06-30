"""
Alimentar modulos
"""
import click

from plataforma_web.blueprints.modulos.models import Modulo


def alimentar_modulos():
    """Alimentar modulos"""
    Modulo(nombre="ABOGADOS").save()
    Modulo(nombre="AUDIENCIAS").save()
    Modulo(nombre="AUTORIDADES").save()
    Modulo(nombre="DISTRITOS").save()
    Modulo(nombre="EDICTOS").save()
    Modulo(nombre="GLOSAS").save()
    Modulo(nombre="LISTAS DE ACUERDOS").save()
    Modulo(nombre="MATERIAS").save()
    Modulo(nombre="PERITOS").save()
    Modulo(nombre="SENTENCIAS").save()
    Modulo(nombre="UBICACIONES DE EXPEDIENTES").save()
    Modulo(nombre="USUARIOS").save()
    click.echo("  Modulos alimentados.")
