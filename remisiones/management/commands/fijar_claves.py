import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

CLAVE_DE_EJEMPLO = "Ilux2026*"


class Command(BaseCommand):
    help = "Cambia la clave de los usuarios admin y almacen. Lee la nueva clave de la variable ILUX_CLAVE."

    def handle(self, *args, **opts):
        clave = os.environ.get("ILUX_CLAVE", "")
        if len(clave) < 8:
            raise CommandError("ILUX_CLAVE debe tener al menos 8 caracteres.")
        if clave == CLAVE_DE_EJEMPLO:
            raise CommandError("Elige una clave distinta de la de ejemplo.")
        User = get_user_model()
        for nombre in ("admin", "almacen"):
            u = User.objects.filter(username=nombre).first()
            if u:
                u.set_password(clave)
                u.save(update_fields=["password"])
                self.stdout.write(f"Clave actualizada para {nombre}.")
