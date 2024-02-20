from datetime import datetime, timedelta
import logging

import click

from plataforma_web.app import create_app
from plataforma_web.extensions import db
from plataforma_web.blueprints.autoridades.models import Autoridad
from plataforma_web.blueprints.edictos.models import Edicto
from plataforma_web.blueprints.edictos_acuses.models import EdictoAcuse

app = create_app()
db.app = app

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("edictos_acuses.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)


@click.group()
def cli():
    """Edictos"""


@click.command()
def republicar():
    """Republicar edictos para la fecha actual"""

    # Obtener la fecha de hoy
    fecha_actual = datetime.now().date()

    try:
        # Consultar EdictoAcuse, filtrado por la fecha de hoy
        edictos_acuses_hoy = EdictoAcuse.query.filter_by(fecha=fecha_actual).all()

        # Obtener los id de los edictos para republicar
        edictos_id_republicar = set(acuse.edicto_id for acuse in edictos_acuses_hoy)

        # Consultar los Edicto a republicar
        edictos_a_republicar = Edicto.query.filter(Edicto.id.in_(edictos_id_republicar)).all()

        print(edictos_a_republicar)

        # Inicializar un contador de republicaciones
        contador = 0

        for edicto_acuse in edictos_acuses_hoy:
            # Consultar si el edicto ya está republicado para hoy
            if Edicto.query.filter_by(id=edicto_acuse.edicto_id, fecha=fecha_actual).first():
                bitacora.info(f"El edicto con ID %s {edicto_acuse.edicto_id} ya está republicado para hoy")
                continue

            # Obtener el Edicto original
            edicto = Edicto.query.get(edicto_acuse.edicto_id)
            if not edicto:
                bitacora.error(f"No se encontró el Edicto con ID %s {edicto_acuse.edicto_id}")
                continue

            # Crear una copia del edicto republicado con un nuevo ID
            nuevo_edicto = Edicto(
                fecha=fecha_actual,
                descripcion=edicto.descripcion,
                archivo=edicto.archivo,
                url=edicto.url,
                republicado=True,
                autoridad_id=edicto.autoridad_id,
            )
            db.session.add(nuevo_edicto)
            db.session.commit()
            print(f"Nuevo edicto republicado: {nuevo_edicto} con ID {nuevo_edicto.id}")
            click.echo(f"se republico {nuevo_edicto}")
            # Actualizar la fecha del nuevo edicto republicado
            nuevo_edicto.fecha = fecha_actual
            contador += 1

        # Mostrar un mensaje de término
        mensaje = f"Republicados {contador} edictos para hoy ({fecha_actual})"
        bitacora.info(mensaje)
        click.echo(mensaje)

    except Exception as e:
        # En caso de error, registrar el mensaje en la bitácora
        bitacora.error(f"Error al republicar edictos %s: {e}")
        click.echo(f"Error al republicar edictos %s: {e}")


cli.add_command(republicar)
