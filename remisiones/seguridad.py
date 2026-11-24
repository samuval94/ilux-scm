"""Piezas de seguridad: sesiones con vencimiento, bloqueo por intentos fallidos y cabeceras HTTP."""
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

MAX_INTENTOS = 5          # fallos seguidos permitidos por usuario
BLOQUEO_SEGUNDOS = 15 * 60


def token_vencido(token):
    return token.created + timedelta(hours=settings.SESION_HORAS) < timezone.now()


class TokenConVencimiento(TokenAuthentication):
    """Igual que TokenAuthentication, pero la sesión muere SESION_HORAS horas después de iniciarla."""

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if token_vencido(token):
            token.delete()
            raise AuthenticationFailed("La sesión venció. Inicia sesión de nuevo.")
        return user, token


class ControlIntentos:
    """Cuenta los fallos de inicio de sesión por nombre de usuario (exista o no, para no revelar cuáles existen)."""

    @staticmethod
    def _clave(usuario):
        return "login-fallos:" + (usuario or "").strip().lower()[:150]

    @classmethod
    def segundos_de_bloqueo(cls, usuario):
        datos = cache.get(cls._clave(usuario))
        if datos and datos["fallos"] >= MAX_INTENTOS:
            return max(1, int(datos["hasta"] - timezone.now().timestamp()))
        return 0

    @classmethod
    def registrar_fallo(cls, usuario):
        clave = cls._clave(usuario)
        datos = cache.get(clave) or {"fallos": 0, "hasta": 0}
        datos["fallos"] += 1
        datos["hasta"] = timezone.now().timestamp() + BLOQUEO_SEGUNDOS
        cache.set(clave, datos, BLOQUEO_SEGUNDOS)

    @classmethod
    def limpiar(cls, usuario):
        cache.delete(cls._clave(usuario))


# Política de contenido: solo recursos propios. 'unsafe-inline' solo en estilos (React y el lector de códigos los usan).
CSP_APP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
    "font-src 'self' data:; connect-src 'self'; media-src 'self' blob:; worker-src 'self'; manifest-src 'self'; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)
CSP_ADMIN = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)


class CabecerasSeguridad:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        resp = self.get_response(request)
        resp.setdefault("Content-Security-Policy", CSP_ADMIN if request.path.startswith("/admin/") else CSP_APP)
        resp.setdefault("Permissions-Policy", "camera=(self), microphone=(), geolocation=(), payment=(), usb=()")
        if request.path.startswith("/api/"):
            resp["Cache-Control"] = "no-store"
        return resp
