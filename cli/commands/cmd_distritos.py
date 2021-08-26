"""
Distritos

- respaldar: Respaldar a un archivo CSV
"""
from pathlib import Path
import csv
import click

from plataforma_web.app import create_app
from plataforma_web.extensions import db

from plataforma_web.blueprints.distritos.models import Distrito

app = create_app()
db.app = app


@click.group()
def cli():
    """Distritos"""


@click.command()
@click.argument("salida_csv")
def respaldar(salida_csv):
    """Respaldar a un archivo CSV"""
    ruta = Path(salida_csv)
    if ruta.exists():
        click.echo(f"AVISO: {ruta.name} existe, no voy a sobreescribirlo.")
        return
    click.echo("Respaldando distritos...")
    contador = 0
    distritos = Distrito.query.order_by(Distrito.id).all()
    with open(ruta, "w") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(["id", "nombre", "nombre_corto", "es_distrito_judicial", "estatus"])
        for distrito in distritos:
            respaldo.writerow(
                [
                    distrito.id,
                    distrito.nombre,
                    distrito.nombre_corto,
                    int(distrito.es_distrito_judicial),
                    distrito.estatus,
                ]
            )
            contador += 1
    click.echo(f"Respaldados {contador} distritos.")


cli.add_command(respaldar)
