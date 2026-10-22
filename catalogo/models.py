from django.db import models


class Grupo(models.Model):
    nombre = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "grupo de materiales"
        verbose_name_plural = "grupos de materiales"

    def __str__(self):
        return self.nombre


class Material(models.Model):
    class Unidad(models.TextChoices):
        UNIDAD = "UNIDAD", "Unidad"
        METRO = "MT", "Metro"
        TRAMO = "TR", "Tramo"
        KILO = "KG", "Kilogramo"
        CANECA = "CANECA", "Caneca"

    
    class Tipo(models.TextChoices):
        MATERIAL = "MATERIAL", "Material"
        HERRAMIENTA = "HERRAMIENTA", "Herramienta"
        EQUIPO = "EQUIPO", "Equipo"

    UNIDADES_DECIMALES = ("MT", "KG")

    # Texto y no número: hay códigos como "609009-1" o "H00001002"
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=255, db_index=True)
    grupo = models.ForeignKey(Grupo, on_delete=models.PROTECT, related_name="materiales")
    unidad = models.CharField(max_length=10, choices=Unidad.choices)
    tipo = models.CharField(max_length=12, choices=Tipo.choices, default=Tipo.MATERIAL)
    # Se desactiva en vez de borrar: las remisiones antiguas lo van a referenciar
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "materiales"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def admite_decimales(self):
        return self.unidad in self.UNIDADES_DECIMALES

    