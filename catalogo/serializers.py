from rest_framework import serializers

from .models import Grupo, Material


class MaterialSerializer(serializers.ModelSerializer):
    grupo = serializers.CharField(source="grupo.nombre", read_only=True)
    grupo_nombre = serializers.CharField(write_only=True, required=False, max_length=80)
    admite_decimales = serializers.BooleanField(read_only=True)

    class Meta:
        model = Material
        fields = ["id", "codigo", "nombre", "grupo", "grupo_nombre", "unidad", "tipo", "activo", "admite_decimales"]

    def validate_codigo(self, v):
        return v.strip()

    def validate_nombre(self, v):
        return v.strip().upper()

    def create(self, validated):
        nombre_grupo = validated.pop("grupo_nombre", "").strip().upper() or "VARIOS"
        grupo, _ = Grupo.objects.get_or_create(nombre=nombre_grupo)
        return Material.objects.create(grupo=grupo, **validated)

    def update(self, instance, validated):
        nombre_grupo = validated.pop("grupo_nombre", "").strip().upper()
        if nombre_grupo:
            instance.grupo, _ = Grupo.objects.get_or_create(nombre=nombre_grupo)
        for k, v in validated.items():
            setattr(instance, k, v)
        instance.save()
        return instance


class MaterialCompactoSerializer(serializers.ModelSerializer):
    """Formato liviano para guardar el catálogo completo en el dispositivo (modo sin conexión)."""

    grupo = serializers.CharField(source="grupo.nombre")
    admite_decimales = serializers.BooleanField()

    class Meta:
        model = Material
        fields = ["id", "codigo", "nombre", "grupo", "unidad", "tipo", "admite_decimales"]


class GrupoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grupo
        fields = ["id", "nombre"]
