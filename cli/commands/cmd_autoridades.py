"""
Autoridades

- respaldar: Respaldar a un archivo CSV
"""
from pathlib import Path
import csv
import click

from plataforma_web.app import create_app
from plataforma_web.extensions import db

from plataforma_web.blueprints.autoridades.models import Autoridad

app = create_app()
db.app = app


@click.group()
def cli():
    """Autoridades"""


@click.command()
@click.argument("salida_csv")
def respaldar(salida_csv):
    """Respaldar a un archivo CSV"""
    ruta = Path(salida_csv)
    if ruta.exists():
        click.echo(f"AVISO: {ruta.name} existe, no voy a sobreescribirlo.")
        return
    click.echo("Respaldando autoridades...")
    contador = 0
    autoridades = Autoridad.query.order_by(Autoridad.id).all()
    with open(ruta, "w") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "id",
                "distrito_id",
                "materia_id",
                "clave",
                "descripcion",
                "descripcion_corta",
                "es_jurisdiccional",
                "es_notaria",
                "organo_jurisdiccional",
                "directorio_edictos",
                "directorio_glosas",
                "directorio_listas_de_acuerdos",
                "directorio_sentencias",
                "audiencia_categoria",
                "estatus",
            ]
        )
        for autoridad in autoridades:
            respaldo.writerow(
                [
                    autoridad.id,
                    autoridad.distrito_id,
                    autoridad.materia_id,
                    autoridad.clave,
                    autoridad.descripcion,
                    autoridad.descripcion_corta,
                    int(autoridad.es_jurisdiccional),
                    int(autoridad.es_notaria),
                    autoridad.organo_jurisdiccional,
                    autoridad.directorio_edictos,
                    autoridad.directorio_glosas,
                    autoridad.directorio_listas_de_acuerdos,
                    autoridad.directorio_sentencias,
                    autoridad.audiencia_categoria,
                    autoridad.estatus,
                ]
            )
            contador += 1
    click.echo(f"Respaldadas {contador} autoridades.")


cli.add_command(respaldar)
