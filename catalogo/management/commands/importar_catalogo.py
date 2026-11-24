from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from catalogo.services import ErrorImportacion, importar


class Command(BaseCommand):
    help = "Importa o actualiza el catálogo desde un Excel o CSV (por código)."

    def add_arguments(self, parser):
        parser.add_argument("archivo")
        parser.add_argument(
            "--desactivar-faltantes",
            action="store_true",
            help="Marca como inactivos los materiales que no vienen en el archivo.",
        )

    def handle(self, *args, archivo, desactivar_faltantes, **opts):
        ruta = Path(archivo)
        if not ruta.exists():
            raise CommandError(f"No existe: {ruta}")
        try:
            r = importar(ruta, ruta.name, desactivar_faltantes)
        except ErrorImportacion as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(
            f"Catálogo listo: {r['creados']} creados, {r['actualizados']} actualizados, "
            f"{r['desactivados']} desactivados."
        ))
