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
    """Una sola fila que lleva el último número de remisión (se bloquea al usarla)."""

    ultimo = models.PositiveIntegerField(default=0)

    @classmethod
    def siguiente(cls):
        fila, _ = cls.objects.select_for_update().get_or_create(pk=1)
        fila.ultimo += 1
        fila.save(update_fields=["ultimo"])
        return fila.ultimo


class Remision(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        FIRMADA = "FIRMADA", "Firmada"
        ANULADA = "ANULADA", "Anulada"

    # UUID generado por el cliente: permite trabajar sin conexión y reenviar sin duplicar
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # El número oficial se asigna al firmar
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
    actualizada_en = models.DateTimeField(auto_now=True)
    firmada_en = models.DateTimeField(null=True, blank=True)
    # Anulación (solo desde FIRMADA, con motivo obligatorio)
    motivo_anulacion = models.TextField(blank=True)
    anulada_en = models.DateTimeField(null=True, blank=True)
    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="remisiones_anuladas",
    )

    class Meta:
        ordering = ["-creada_en"]

    def __str__(self):
        return f"Remisión {self.numero_formato or 'borrador'} - {self.proyecto}"

    @property
    def numero_formato(self):
        return f"{self.numero:06d}" if self.numero else None

    def save(self, *args, **kwargs):
        if not self._state.adding:
            anterior = Remision.objects.filter(pk=self.pk).values_list("estado", flat=True).first()
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
        if not (nombre or "").strip() or not (cedula or "").strip():
            raise ValidationError("La firma requiere nombre y cédula de quien recibe.")
        Firma.objects.create(
            remision=self, imagen=archivo_firma, nombre=nombre.strip(), cedula=cedula.strip(), ip=ip
        )
        self.numero = Consecutivo.siguiente()
        self.estado = self.Estado.FIRMADA
        self.firmada_en = timezone.now()
        self.save()

    @transaction.atomic
    def anular(self, usuario, motivo):
        if self.estado != self.Estado.FIRMADA:
            raise ValidationError("Solo se puede anular una remisión firmada (un borrador se elimina).")
        motivo = (motivo or "").strip()
        if len(motivo) < 5:
            raise ValidationError("Escribe el motivo de la anulación (mínimo 5 caracteres).")
        self.estado = self.Estado.ANULADA
        self.motivo_anulacion = motivo
        self.anulada_en = timezone.now()
        self.anulada_por = usuario
        self.save()


class ItemRemision(models.Model):
    remision = models.ForeignKey(Remision, on_delete=models.CASCADE, related_name="items")
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    observacion = models.CharField(max_length=255, blank=True)
    # Solo herramientas/equipos: fecha en la que se espera la devolución
    devolver_antes_de = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["remision", "material"], name="material_unico_por_remision"),
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name="cantidad_positiva"),
        ]

    def _validar_borrador(self):
        if self.remision.estado != Remision.Estado.BORRADOR:
            raise ValidationError("Solo se pueden modificar ítems de una remisión en borrador.")

    def clean(self):
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


class Devolucion(models.Model):
    """Registro de que una herramienta o equipo entregado fue devuelto."""

    item = models.OneToOneField(ItemRemision, on_delete=models.PROTECT, related_name="devolucion")
    devuelta_en = models.DateTimeField(default=timezone.now)
    recibida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="devoluciones_recibidas"
    )
    observacion = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-devuelta_en"]
