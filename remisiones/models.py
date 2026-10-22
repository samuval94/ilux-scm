import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from catalogo.models import Material


class Empleado(models.Model):
    """Quien puede recibir: el técnico o cualquier empleado de Ilux."""

    nombre = models.CharField(max_length=150)
    cedula = models.CharField(max_length=20, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.cedula})"


class Proyecto(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Consecutivo(models.Model):
    """Una sola fila que lleva el último número de remisión."""

    ultimo = models.PositiveIntegerField(default=0)

    @classmethod
    def siguiente(cls):
        # select_for_update bloquea la fila: dos firmas simultáneas no obtienen el mismo número
        fila, _ = cls.objects.select_for_update().get_or_create(pk=1)
        fila.ultimo += 1
        fila.save(update_fields=["ultimo"])
        return fila.ultimo


class Remision(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        FIRMADA = "FIRMADA", "Firmada"
        ANULADA = "ANULADA", "Anulada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.PositiveIntegerField(unique=True, null=True, blank=True, editable=False)
    proyecto = models.ForeignKey(Proyecto, on_delete=models.PROTECT, related_name="remisiones")
    entregada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="remisiones_entregadas"
    )
    recibida_por = models.ForeignKey(
        Empleado, on_delete=models.PROTECT, related_name="remisiones_recibidas"
    )
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.BORRADOR)
    observaciones = models.TextField(blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    firmada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creada_en"]
        verbose_name = "remisión"
        verbose_name_plural = "remisiones"

    def __str__(self):
        return f"Remisión {self.numero or 'borrador'} - {self.proyecto}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            anterior = (
                Remision.objects.filter(pk=self.pk).values_list("estado", flat=True).first()
            )
            if anterior == self.Estado.ANULADA:
                raise ValidationError("Una remisión anulada no se puede modificar.")
            if anterior == self.Estado.FIRMADA and self.estado != self.Estado.ANULADA:
                raise ValidationError(
                    "Una remisión firmada no se puede modificar: anúlala y crea una nueva."
                )
        super().save(*args, **kwargs)

    @transaction.atomic
    def firmar(self, archivo_firma, nombre, cedula, ip=None):
        if self.estado != self.Estado.BORRADOR:
            raise ValidationError("Solo se puede firmar una remisión en borrador.")
        if not self.items.exists():
            raise ValidationError("La remisión no tiene ítems.")
        Firma.objects.create(
            remision=self, imagen=archivo_firma, nombre=nombre, cedula=cedula, ip=ip
        )
        self.numero = Consecutivo.siguiente()
        self.estado = self.Estado.FIRMADA
        self.firmada_en = timezone.now()
        self.save()


class ItemRemision(models.Model):
    remision = models.ForeignKey(Remision, on_delete=models.CASCADE, related_name="items")
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    observacion = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["remision", "material"], name="material_unico_por_remision"
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0), name="cantidad_positiva"
            ),
        ]

    def _validar_borrador(self):
        if self.remision.estado != Remision.Estado.BORRADOR:
            raise ValidationError("Solo se pueden modificar ítems de una remisión en borrador.")

    def clean(self):
        if not self.remision_id or not self.material_id or self.cantidad is None:
            return  # los campos obligatorios vacíos los reporta el formulario
        self._validar_borrador()
        cantidad = Decimal(str(self.cantidad))
        if cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor que cero.")
        if not self.material.admite_decimales and cantidad != cantidad.to_integral_value():
            raise ValidationError(
                f"'{self.material.nombre}' se maneja en {self.material.unidad}: "
                "la cantidad debe ser un número entero."
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self._validar_borrador()
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} {self.material.unidad} - {self.material.nombre}"


class Firma(models.Model):
    remision = models.OneToOneField(Remision, on_delete=models.PROTECT, related_name="firma")
    imagen = models.FileField(upload_to="firmas/%Y/%m/")
    nombre = models.CharField(max_length=150)
    cedula = models.CharField(max_length=20)
    firmada_en = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)