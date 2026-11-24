from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Grupo, Material
from .serializers import GrupoSerializer, MaterialCompactoSerializer, MaterialSerializer
from .services import ErrorImportacion, importar


class EsAdminOLectura(BasePermission):
    """Lectura para cualquier usuario autenticado; escritura solo para administradores."""

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or request.user.is_staff


class EsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class MaterialViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = MaterialSerializer
    permission_classes = [EsAdminOLectura]

    def get_queryset(self):
        qs = Material.objects.select_related("grupo")
        p = self.request.query_params
        if p.get("activo") in ("0", "1"):
            qs = qs.filter(activo=p["activo"] == "1")
        elif self.action == "list" and p.get("todos") != "1":
            qs = qs.filter(activo=True)
        if p.get("tipo"):
            qs = qs.filter(tipo=p["tipo"].upper())
        if p.get("grupo"):
            qs = qs.filter(grupo__nombre=p["grupo"])
        q = (p.get("search") or "").strip()
        if q:
            cond = Q()
            for palabra in q.split():
                cond &= Q(nombre__icontains=palabra) | Q(codigo__icontains=palabra)
            qs = qs.filter(cond)
        return qs

    @action(detail=False, methods=["get"], url_path="catalogo")
    def catalogo(self, request):
        """Catálogo completo (solo activos), sin paginar: se guarda en el dispositivo."""
        qs = Material.objects.select_related("grupo").filter(activo=True)
        return Response(MaterialCompactoSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path=r"por-codigo/(?P<codigo>[^/]+)")
    def por_codigo(self, request, codigo):
        m = Material.objects.select_related("grupo").filter(codigo__iexact=codigo.strip()).first()
        if not m:
            raise NotFound("No existe un material con ese código.")
        if not m.activo:
            raise ValidationError("Ese material está inactivo en el catálogo.")
        return Response(MaterialSerializer(m).data)


class GrupoListView(APIView):
    def get(self, request):
        return Response(GrupoSerializer(Grupo.objects.all(), many=True).data)


class ImportarCatalogoView(APIView):
    permission_classes = [EsAdmin]

    def post(self, request):
        archivo = request.FILES.get("archivo")
        if not archivo:
            raise ValidationError("Adjunta un archivo en el campo 'archivo'.")
        desactivar = str(request.data.get("desactivar_faltantes", "")).lower() in ("1", "true", "si", "sí")
        try:
            resultado = importar(archivo, archivo.name, desactivar)
        except ErrorImportacion as exc:
            raise ValidationError(str(exc))
        return Response(resultado, status=status.HTTP_200_OK)
