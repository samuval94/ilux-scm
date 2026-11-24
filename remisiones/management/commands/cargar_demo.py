from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from catalogo.models import Material
from catalogo.services import importar
from remisiones.models import Empleado, Proyecto

PROYECTOS = [
    "Estación de servicio Terpel – La Estrella",
    "Mantenimiento subestación Sabaneta",
    "Sistema solar fotovoltaico – Planta Envigado",
    "Redes y cableado estructurado – Oficinas El Poblado",
]
EMPLEADOS = [
    ("Carlos Andrés Restrepo", "1017000001"),
    ("Luis Fernando Zapata", "1017000002"),
    ("Andrés Felipe Gómez", "1017000003"),
    ("Jeniffer Correa", "43000004"),
]


class Command(BaseCommand):
    help = "Crea usuarios, proyectos y empleados de demostración y carga el catálogo si está vacío."

    def add_arguments(self, parser):
        parser.add_argument("--catalogo", default=str(Path(settings.BASE_DIR) / "data" / "BASE_DE_DATOS_MATERIAL.xls"))

    def handle(self, *args, catalogo, **opts):
        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@ilux.local", "Ilux2026*", first_name="Administrador", last_name="ILUX")
            self.stdout.write("Usuario creado: admin / Ilux2026*  (administrador)")
        if not User.objects.filter(username="almacen").exists():
            User.objects.create_user("almacen", "almacen@ilux.local", "Ilux2026*", first_name="Compras y", last_name="Almacén")
            self.stdout.write("Usuario creado: almacen / Ilux2026*  (operador)")
        for n in PROYECTOS:
            Proyecto.objects.get_or_create(nombre=n)
        for nombre, cc in EMPLEADOS:
            Empleado.objects.get_or_create(cedula=cc, defaults={"nombre": nombre})
        if not Material.objects.exists():
            ruta = Path(catalogo)
            if ruta.exists():
                r = importar(ruta, ruta.name)
                self.stdout.write(f"Catálogo importado: {r['creados']} materiales.")
            else:
                self.stdout.write(self.style.WARNING(f"No se encontró {ruta}: importa el catálogo con 'importar_catalogo'."))
        self.stdout.write(self.style.SUCCESS("Datos de demostración listos."))
