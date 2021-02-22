"""
Abogados

- alimentar: Alimentar la tabla abogados insertando registros desde un archivo CSV
- respaldar: Respaldar la tabla 'abogados' a su archivo CSV
"""
from datetime import datetime
from pathlib import Path
import csv
from unidecode import unidecode
import click

from plataforma_web.app import create_app
from plataforma_web.extensions import db

from plataforma_web.blueprints.abogados.models import Abogado

app = create_app()
db.app = app


@click.group()
def cli():
    """ Grupo para una orden click """


@click.command()
@click.argument("entrada_csv")
def alimentar(entrada_csv):
    """ Alimentar la tabla abogados insertando registros desde un archivo CSV """
    ruta = Path(entrada_csv)
    if not ruta.exists():
        click.echo(f"AVISO: {ruta.name} no se encontró.")
        return
    if not ruta.is_file():
        click.echo(f"AVISO: {ruta.name} no es un archivo.")
        return
    click.echo("Alimentando abogados...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            try:
                fecha = datetime.strptime(row["fecha"].strip(), "%Y-%m-%d")  # Probar que fecha sea correcta
            except ValueError as mensaje:
                click.echo(f"  Dato con error: {mensaje}")
                continue
            datos = {
                "numero": row["numero"].strip(),  # Hay números como 000-Bis
                "nombre": unidecode(row["nombre"].strip()).upper(),  # Nombre sin acentos y en mayúsculas
                "libro": row["libro"].strip(),
                "fecha": fecha,
            }
            Abogado(**datos).save()
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador} registros...")
    click.echo(f"- {contador} abogados alimentados.")


@click.command()
@click.argument("salida_csv")
@click.option("--desde", default="", type=str, help="Fecha de inicio, use AAAA-MM-DD")
def respaldar(desde, salida_csv):
    """ Respaldar la tabla abogados a su archivo CSV """
    ruta = Path(salida_csv)
    if ruta.exists():
        click.echo(f"AVISO: {ruta.name} existe, no voy a sobreescribirlo.")
        return
    if desde != "":
        try:
            desde_fecha = datetime.strptime(desde, "%Y-%m-%d")
        except ValueError as mensaje:
            click.echo(f"AVISO: Fecha de inicio es incorrecta: {mensaje}")
            return
    else:
        desde_fecha = None
    click.echo("Respaldando abogados...")
    contador = 0
    abogados = Abogado.query.filter(Abogado.estatus == "A")
    if desde_fecha is not None:
        abogados = abogados.filter(Abogado.fecha >= desde_fecha)
    abogados = abogados.order_by(Abogado.fecha).all()
    with open(ruta, "w") as puntero:
        escritor = csv.writer(puntero)
        escritor.writerow(["numero", "nombre", "libro", "fecha"])
        for abogado in abogados:
            escritor.writerow(
                [
                    abogado.numero,
                    abogado.nombre,
                    abogado.libro,
                    abogado.fecha.strftime("%Y-%m-%d"),
                ]
            )
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador} registros...")
    click.echo(f"Respaldados {contador} registros.")


cli.add_command(alimentar)
cli.add_command(respaldar)