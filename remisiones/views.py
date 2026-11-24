from datetime import timedelta

from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import mixins, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, Throttled, ValidationError
from rest_framework.permissions import SAFE_METHODS, AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogo.models import Material

from .models import Devolucion, Empleado, ItemRemision, Proyecto, Remision
from .serializers import (
    EmpleadoSerializer, GuardarRemisionSerializer, ItemSerializer, ProyectoSerializer,
    RemisionDetailSerializer, RemisionListSerializer, archivo_de_firma,
)
from .services.excel import excel_herramientas, excel_pendientes_firma, excel_remisiones
from .seguridad import ControlIntentos, token_vencido
from .services.pdf import generar_pdf

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class EsAdminOLectura(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or request.user.is_staff


def es_admin(user):
    return bool(user.is_staff or user.is_superuser)


def datos_usuario(user):
    return {
        "id": user.id,
        "username": user.username,
        "nombre": user.get_full_name() or user.username,
        "rol": "ADMIN" if es_admin(user) else "OPERADOR",
    }


# ---------------- Autenticación ------------------------------------------------------------

class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        usuario = (request.data.get("username") or "").strip()
        espera = ControlIntentos.segundos_de_bloqueo(usuario)
        if espera:
            minutos = -(-espera // 60)
            raise Throttled(wait=espera, detail=f"Demasiados intentos fallidos. Intenta de nuevo en {minutos} minuto(s).")
        user = authenticate(username=usuario, password=request.data.get("password") or "")
        if not user or not user.is_active:
            ControlIntentos.registrar_fallo(usuario)
            raise ValidationError("Usuario o contraseña incorrectos.")
        ControlIntentos.limpiar(usuario)
        token, creado = Token.objects.get_or_create(user=user)
        if not creado and token_vencido(token):
            token.delete()
            token = Token.objects.create(user=user)
        return Response({"token": token.key, "user": datos_usuario(user)})


class LogoutView(APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(datos_usuario(request.user))


# ---------------- Proyectos y empleados -----------------------------------------------------

class ProyectoViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = ProyectoSerializer
    permission_classes = [EsAdminOLectura]
    pagination_class = None

    def get_queryset(self):
        qs = Proyecto.objects.all()
        if self.request.query_params.get("todos") != "1":
            qs = qs.filter(activo=True)
        return qs


class EmpleadoViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = EmpleadoSerializer
    permission_classes = [EsAdminOLectura]
    pagination_class = None

    def get_queryset(self):
        qs = Empleado.objects.all()
        if self.request.query_params.get("todos") != "1":
            qs = qs.filter(activo=True)
        return qs


# ---------------- Remisiones ----------------------------------------------------------------

def base_queryset():
    return Remision.objects.select_related(
        "proyecto", "recibida_por", "entregada_por", "anulada_por", "firma"
    ).prefetch_related(
        Prefetch("items", queryset=ItemRemision.objects.select_related("material", "devolucion").order_by("id"))
    )


def filtrar(qs, p):
    if p.get("estado"):
        qs = qs.filter(estado=p["estado"].upper())
    if p.get("proyecto"):
        qs = qs.filter(proyecto_id=p["proyecto"])
    if p.get("recibida_por"):
        qs = qs.filter(recibida_por_id=p["recibida_por"])
    if p.get("mias") == "1":
        qs = qs.filter(entregada_por=p["_user"])
    desde, hasta = parse_date(p.get("desde") or ""), parse_date(p.get("hasta") or "")
    if desde:
        qs = qs.filter(creada_en__date__gte=desde)
    if hasta:
        qs = qs.filter(creada_en__date__lte=hasta)
    q = (p.get("q") or "").strip()
    if q:
        cond = Q(proyecto__nombre__icontains=q) | Q(recibida_por__nombre__icontains=q)
        if q.isdigit():
            cond |= Q(numero=int(q))
        qs = qs.filter(cond)
    return qs


class RemisionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    def get_queryset(self):
        return base_queryset()

    def get_serializer_class(self):
        return RemisionDetailSerializer if self.action == "retrieve" else RemisionListSerializer

    def filter_queryset(self, qs):
        params = {k: v for k, v in self.request.query_params.items()}
        params["_user"] = self.request.user
        return filtrar(qs, params)

    def destroy(self, request, *args, **kwargs):
        r = self.get_object()
        if r.estado != Remision.Estado.BORRADOR:
            raise ValidationError("Solo se puede eliminar un borrador. Una remisión firmada se anula.")
        if r.entregada_por_id != request.user.id and not es_admin(request.user):
            raise PermissionDenied("Solo quien creó el borrador o un administrador puede eliminarlo.")
        r.items.all().delete()
        r.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="guardar")
    @transaction.atomic
    def guardar(self, request):
        """Crea o actualiza un borrador y, opcionalmente, lo firma (todo en una sola llamada).

        Es idempotente por UUID: si el celular reenvía una remisión que ya quedó firmada, devuelve la existente.
        """
        s = GuardarRemisionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        r = Remision.objects.select_for_update().filter(pk=d["id"]).first()
        if r is not None:
            if r.entregada_por_id != request.user.id and not es_admin(request.user):
                raise PermissionDenied("Esta remisión pertenece a otro usuario.")
            if r.estado != Remision.Estado.BORRADOR:
                if d["firmar"] and r.estado == Remision.Estado.FIRMADA:
                    return Response(RemisionDetailSerializer(base_queryset().get(pk=r.pk)).data)
                raise ValidationError("Esta remisión ya no es un borrador y no se puede modificar.")
            r.proyecto, r.recibida_por, r.observaciones = d["proyecto"], d["recibida_por"], d["observaciones"]
            r.save()
            r.items.all().delete()
        else:
            r = Remision.objects.create(
                id=d["id"], proyecto=d["proyecto"], recibida_por=d["recibida_por"],
                observaciones=d["observaciones"], entregada_por=request.user,
            )

        materiales = {m.id: m for m in Material.objects.filter(id__in=[i["material"] for i in d["items"]])}
        for it in d["items"]:
            m = materiales.get(it["material"])
            if m is None or not m.activo:
                raise ValidationError(f"El material con id {it['material']} no existe o está inactivo.")
            ItemRemision(
                remision=r, material=m, cantidad=it["cantidad"], observacion=it["observacion"],
                devolver_antes_de=it["devolver_antes_de"] if m.tipo != Material.Tipo.MATERIAL else None,
            ).save()

        if d["firmar"]:
            f = d["firma"]
            ip = (request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR")) or None
            r.firmar(
                archivo_de_firma(f, r.id),
                f.get("nombre") or r.recibida_por.nombre,
                f.get("cedula") or r.recibida_por.cedula,
                ip,
            )
        r = base_queryset().get(pk=r.pk)
        return Response(RemisionDetailSerializer(r).data, status=status.HTTP_201_CREATED if d["firmar"] else status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="anular")
    def anular(self, request, pk=None):
        if not es_admin(request.user):
            raise PermissionDenied("Solo un administrador puede anular remisiones.")
        r = self.get_object()
        r.anular(request.user, request.data.get("motivo"))
        return Response(RemisionDetailSerializer(base_queryset().get(pk=r.pk)).data)

    @action(detail=True, methods=["get"], url_path="pdf")
    def pdf(self, request, pk=None):
        r = self.get_object()
        base = request.build_absolute_uri("/")
        from django.conf import settings
        if settings.URL_PUBLICA:
            base = settings.URL_PUBLICA.rstrip("/") + "/"
        contenido = generar_pdf(r, f"{base}verificar/{r.id}")
        resp = HttpResponse(contenido, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="Remision_{r.numero_formato or "borrador_" + str(r.id)[:8]}.pdf"'
        return resp

    @action(detail=True, methods=["get"], url_path="excel")
    def excel(self, request, pk=None):
        r = self.get_object()
        resp = HttpResponse(excel_remisiones([r]), content_type=XLSX)
        resp["Content-Disposition"] = f'attachment; filename="Remision_{r.numero_formato or "borrador"}.xlsx"'
        return resp

    @action(detail=True, methods=["get"], url_path="firma")
    def firma(self, request, pk=None):
        r = self.get_object()
        if not hasattr(r, "firma"):
            raise NotFound("Esta remisión no tiene firma.")
        return FileResponse(r.firma.imagen.open("rb"), content_type="image/png")

    @action(detail=False, methods=["get"], url_path="exportar")
    def exportar(self, request):
        """Excel con todas las remisiones que cumplan los filtros (mismos parámetros que el listado).
        Con ?formato=pendientes devuelve solo los borradores sin firmar (para Power Automate)."""
        qs = self.filter_queryset(self.get_queryset())
        if request.query_params.get("formato") == "pendientes":
            qs = qs.filter(estado=Remision.Estado.BORRADOR).order_by("creada_en")
            contenido, nombre = excel_pendientes_firma(qs), "Remisiones_pendientes.xlsx"
        else:
            contenido, nombre = excel_remisiones(qs.order_by("numero", "creada_en")), "Remisiones.xlsx"
        resp = HttpResponse(contenido, content_type=XLSX)
        resp["Content-Disposition"] = f'attachment; filename="{nombre}"'
        return resp


# ---------------- Herramientas y equipos ----------------------------------------------------

def items_pendientes():
    return (
        ItemRemision.objects.filter(
            remision__estado=Remision.Estado.FIRMADA,
            material__tipo__in=[Material.Tipo.HERRAMIENTA, Material.Tipo.EQUIPO],
            devolucion__isnull=True,
        )
        .select_related("material", "remision__proyecto", "remision__recibida_por")
        .order_by("devolver_antes_de", "remision__firmada_en")
    )


class HerramientasPendientesView(APIView):
    def get(self, request):
        hoy = timezone.localdate()
        data = []
        for it in items_pendientes():
            r = it.remision
            data.append({
                **ItemSerializer(it).data,
                "remision_id": str(r.id), "remision_numero": r.numero_formato, "proyecto_nombre": r.proyecto.nombre,
                "recibida_por_nombre": r.recibida_por.nombre, "firmada_en": r.firmada_en,
                "vencida": bool(it.devolver_antes_de and it.devolver_antes_de < hoy),
            })
        return Response(data)


class HerramientasPendientesExcelView(APIView):
    def get(self, request):
        resp = HttpResponse(excel_herramientas(items_pendientes()), content_type=XLSX)
        resp["Content-Disposition"] = 'attachment; filename="Herramientas_entregadas.xlsx"'
        return resp


class DevolverItemView(APIView):
    def post(self, request, pk):
        item = ItemRemision.objects.select_related("material", "remision").filter(pk=pk).first()
        if not item:
            raise NotFound("Ítem no encontrado.")
        if item.remision.estado != Remision.Estado.FIRMADA:
            raise ValidationError("Solo se registran devoluciones de remisiones firmadas.")
        if item.material.tipo == Material.Tipo.MATERIAL:
            raise ValidationError("Los materiales consumibles no se devuelven; solo herramientas y equipos.")
        if hasattr(item, "devolucion"):
            raise ValidationError("Este ítem ya fue devuelto.")
        Devolucion.objects.create(item=item, recibida_por=request.user, observacion=(request.data.get("observacion") or "")[:255])
        return Response({"ok": True}, status=status.HTTP_201_CREATED)


# ---------------- Verificación pública (QR) y resumen ---------------------------------------

@api_view(["GET"])
@permission_classes([AllowAny])
def verificar(request, pk):
    try:
        r = Remision.objects.select_related("proyecto").prefetch_related("items").filter(pk=pk).first()
    except Exception:
        r = None
    if not r or r.estado == Remision.Estado.BORRADOR:
        raise NotFound("No se encontró una remisión firmada con ese código.")
    return Response({
        "numero_formato": r.numero_formato, "estado": r.estado, "proyecto_nombre": r.proyecto.nombre,
        "firmada_en": r.firmada_en, "total_items": r.items.count(),
        "anulada": r.estado == Remision.Estado.ANULADA,
    })


@api_view(["GET"])
def resumen(request):
    ahora = timezone.now()
    hoy = timezone.localdate()
    firmadas = Remision.objects.filter(estado=Remision.Estado.FIRMADA).count()
    borradores = Remision.objects.filter(estado=Remision.Estado.BORRADOR)
    pendientes = list(items_pendientes())
    total_proc = firmadas + borradores.count()
    return Response({
        "firmadas_hoy": Remision.objects.filter(estado=Remision.Estado.FIRMADA, firmada_en__date=hoy).count(),
        "firmadas_total": firmadas,
        "borradores": borradores.count(),
        "borradores_antiguos": borradores.filter(creada_en__lt=ahora - timedelta(hours=24)).count(),
        "anuladas": Remision.objects.filter(estado=Remision.Estado.ANULADA).count(),
        "porcentaje_firmadas": round(100 * firmadas / total_proc, 1) if total_proc else None,
        "herramientas_pendientes": len(pendientes),
        "herramientas_vencidas": sum(1 for i in pendientes if i.devolver_antes_de and i.devolver_antes_de < hoy),
    })
