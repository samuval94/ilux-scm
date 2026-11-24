import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

CLAVE_DE_EJEMPLO = "Ilux2026*"


class Command(BaseCommand):
    help = "Cambia la clave de los usuarios admin y almacen. Lee la nueva clave de la variable ILUX_CLAVE."

    def handle(self, *args, **opts):
        clave = os.environ.get("ILUX_CLAVE", "")
        if clave == CLAVE_DE_EJEMPLO:
            raise CommandError("Elige una clave distinta de la de ejemplo.")
        try:
            validate_password(clave)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages))
        User = get_user_model()
        for nombre in ("admin", "almacen"):
            u = User.objects.filter(username=nombre).first()
            if u:
                u.set_password(clave)
                u.save(update_fields=["password"])
                self.stdout.write(f"Clave actualizada para {nombre}.")
