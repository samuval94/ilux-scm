import base64
import binascii
from decimal import Decimal

from django.core.files.base import ContentFile
from rest_framework import serializers

from .models import Empleado, ItemRemision, Proyecto, Remision

MAX_FIRMA_BYTES = 600 * 1024
PNG = b"\x89PNG\r\n\x1a\n"


class ProyectoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proyecto
        fields = ["id", "nombre", "activo"]


class EmpleadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empleado
        fields = ["id", "nombre", "cedula", "activo"]


class ItemSerializer(serializers.ModelSerializer):
    codigo = serializers.CharField(source="material.codigo")
    nombre = serializers.CharField(source="material.nombre")
    unidad = serializers.CharField(source="material.unidad")
    tipo = serializers.CharField(source="material.tipo")
    admite_decimales = serializers.BooleanField(source="material.admite_decimales")
    devuelto = serializers.SerializerMethodField()
    devuelto_en = serializers.SerializerMethodField()

    class Meta:
        model = ItemRemision
        fields = [
            "id", "material", "codigo", "nombre", "unidad", "tipo", "admite_decimales",
            "cantidad", "observacion", "devolver_antes_de", "devuelto", "devuelto_en",
        ]

    def get_devuelto(self, obj):
        return hasattr(obj, "devolucion")

    def get_devuelto_en(self, obj):
        return obj.devolucion.devuelta_en if hasattr(obj, "devolucion") else None


def _nombre(user):
    return (user.get_full_name() or user.username) if user else None


class RemisionListSerializer(serializers.ModelSerializer):
    numero_formato = serializers.CharField(read_only=True)
    proyecto_nombre = serializers.CharField(source="proyecto.nombre", read_only=True)
    entregada_por_nombre = serializers.SerializerMethodField()
    recibida_por_nombre = serializers.CharField(source="recibida_por.nombre", read_only=True)
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Remision
        fields = [
            "id", "numero", "numero_formato", "estado", "proyecto", "proyecto_nombre",
            "entregada_por", "entregada_por_nombre", "recibida_por", "recibida_por_nombre",
            "observaciones", "creada_en", "actualizada_en", "firmada_en", "total_items",
        ]

    def get_entregada_por_nombre(self, obj):
        return _nombre(obj.entregada_por)

    def get_total_items(self, obj):
        return len(obj.items.all())


class RemisionDetailSerializer(RemisionListSerializer):
    items = ItemSerializer(many=True, read_only=True)
    recibida_por_cedula = serializers.CharField(source="recibida_por.cedula", read_only=True)
    firma_nombre = serializers.SerializerMethodField()
    firma_cedula = serializers.SerializerMethodField()
    tiene_firma = serializers.SerializerMethodField()
    anulada_por_nombre = serializers.SerializerMethodField()

    class Meta(RemisionListSerializer.Meta):
        fields = RemisionListSerializer.Meta.fields + [
            "items", "recibida_por_cedula", "firma_nombre", "firma_cedula", "tiene_firma",
            "motivo_anulacion", "anulada_en", "anulada_por_nombre",
        ]

    def get_tiene_firma(self, obj):
        return hasattr(obj, "firma")

    def get_firma_nombre(self, obj):
        return obj.firma.nombre if hasattr(obj, "firma") else None

    def get_firma_cedula(self, obj):
        return obj.firma.cedula if hasattr(obj, "firma") else None

    def get_anulada_por_nombre(self, obj):
        return _nombre(obj.anulada_por)


# ---- Entrada para guardar / firmar ----------------------------------------------------------

class ItemEntradaSerializer(serializers.Serializer):
    material = serializers.IntegerField()
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    observacion = serializers.CharField(max_length=255, allow_blank=True, required=False, default="")
    devolver_antes_de = serializers.DateField(required=False, allow_null=True, default=None)


class FirmaEntradaSerializer(serializers.Serializer):
    imagen = serializers.CharField()  # data URL (PNG en base64) generada por signature_pad
    nombre = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    cedula = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")

    def validate_imagen(self, valor):
        if "," in valor and valor.strip().startswith("data:"):
            valor = valor.split(",", 1)[1]
        try:
            binario = base64.b64decode(valor, validate=True)
        except (binascii.Error, ValueError):
            raise serializers.ValidationError("La firma no es una imagen válida.")
        if not binario.startswith(PNG):
            raise serializers.ValidationError("La firma debe ser una imagen PNG.")
        if len(binario) > MAX_FIRMA_BYTES:
            raise serializers.ValidationError("La imagen de la firma es demasiado grande.")
        return binario


class GuardarRemisionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    proyecto = serializers.PrimaryKeyRelatedField(queryset=Proyecto.objects.filter(activo=True))
    recibida_por = serializers.PrimaryKeyRelatedField(queryset=Empleado.objects.filter(activo=True))
    observaciones = serializers.CharField(allow_blank=True, required=False, default="")
    items = ItemEntradaSerializer(many=True, allow_empty=False)
    firmar = serializers.BooleanField(default=False)
    firma = FirmaEntradaSerializer(required=False)

    def validate_items(self, items):
        vistos = set()
        for it in items:
            if it["material"] in vistos:
                raise serializers.ValidationError("Un material no puede repetirse en la misma remisión.")
            vistos.add(it["material"])
        return items

    def validate(self, datos):
        if datos["firmar"] and not datos.get("firma"):
            raise serializers.ValidationError({"firma": "Falta la firma de quien recibe."})
        return datos


def archivo_de_firma(firma_validada, remision_id):
    return ContentFile(firma_validada["imagen"], name=f"{remision_id}.png")
