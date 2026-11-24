"""Convierte los errores de reglas de negocio (ValidationError de Django) en respuestas 400 claras."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def _texto(errores):
    if isinstance(errores, dict):
        return " ".join(_texto(v) for v in errores.values())
    if isinstance(errores, (list, tuple)):
        return " ".join(_texto(v) for v in errores)
    return str(errores)


def manejador(exc, context):
    if isinstance(exc, DjangoValidationError):
        return Response({"detail": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, IntegrityError):
        return Response(
            {"detail": "No se pudo guardar por una restricción de datos (¿duplicado?)."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    resp = exception_handler(exc, context)
    if resp is not None and "detail" not in (resp.data if isinstance(resp.data, dict) else {}):
        # Unifica: siempre {"detail": "texto legible", "errores": {...}}
        resp.data = {"detail": _texto(resp.data), "errores": resp.data}
    return resp
