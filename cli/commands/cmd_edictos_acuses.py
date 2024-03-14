"""
Edictos Acuses

- republicar: Republicar edictos para hoy o la fecha dada
"""

import sys
from datetime import datetime
import logging
from datetime import datetime

import click

from plataforma_web.app import create_app
from plataforma_web.extensions import db
from plataforma_web.blueprints.edictos.models import Edicto
from plataforma_web.blueprints.edictos_acuses.models import EdictoAcuse

app = create_app()
db.app = app

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/edictos_acuses.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)


@click.group()
@click.pass_context
def cli(ctx):
    """Edictos"""


@click.command()
@click.option("--fecha", default=None, help="Fecha de republicacion")
@click.pass_context
def republicar(ctx, fecha):
    """Republicar edictos para hoy o la fecha dada"""

    # Si no se proporciona la fecha, por defecto se obtiene la fecha de hoy
    if fecha is None:
        fecha = datetime.now().date()

    # Consultar EdictoAcuse, filtrado por la fecha
    edictos_acuses = EdictoAcuse.query.filter_by(fecha=fecha).filter_by(estatus="A").all()

    # Si no hay acuses para la fecha, mostrar mensaje y terminar
    if not edictos_acuses:
        mensaje = f"No hay edictos para republicar para {fecha}"
        click.echo(mensaje)
        bitacora.info(mensaje)
        sys.exit(0)

    # Inicializar un contador de republicaciones
    contador = 0

    # Ciclo por cada EdictoAcuse de hoy
    for edicto_acuse in edictos_acuses:
        mensaje = f"Trabajando con acuse {edicto_acuse.id} del edicto {edicto_acuse.edicto_id}"
        click.echo(mensaje)

        # Para evitar que se republique mas de una vez
        # consultar los Edictos tomando el edicto_id_original y la fecha
        edictos_posibles = Edicto.query.filter_by(edicto_id_original=edicto_acuse.edicto_id).filter_by(fecha=fecha).filter_by(estatus="A").all()

        # Si SI se encontraron edictos_posibles, se omite porque ya estan republicados
        if len(edictos_posibles) > 0:
            mensaje = f"Ya esta republicado el edicto {edicto_acuse.edicto_id} del {fecha}"
            bitacora.warn(mensaje)
            click.echo(mensaje)
            continue

        # En este punto tenemos un edicto_acuse que debe republicarse...

        # Crear un nuevo Edicto para republicar
        nuevo_edicto = Edicto(
            fecha=fecha,
            descripcion=edicto_acuse.edicto.descripcion,
            archivo=edicto_acuse.edicto.archivo,
            url=edicto_acuse.edicto.url,
            autoridad_id=edicto_acuse.edicto.autoridad_id,
            edicto_id_original=edicto_acuse.edicto_id,
        )

        # Guardarlo para obtener su ID
        nuevo_edicto.save()
        # Incrementar contador
        contador += 1

        # Agregar mensaje a la bitacora
        mensaje = f"Edicto republicado: Notaria {nuevo_edicto.autoridad.descripcion_corta}, ID original {edicto_acuse.edicto_id}, ID {nuevo_edicto.id}, fecha {fecha}."
        bitacora.info(mensaje)
        click.echo(mensaje)

    # Mostrar un mensaje de término
    mensaje = f"Se republicaron {contador} edictos para {fecha}"
    bitacora.info(mensaje)
    click.echo(mensaje)


cli.add_command(republicar)
