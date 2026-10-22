import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.db import IntegrityError, transaction

from catalogo.models import Grupo, Material
from remisiones.models import Empleado, ItemRemision, Proyecto, Remision

# Las firmas de prueba se guardan en una carpeta temporal, no en tu carpeta media/
MEDIA_TEMPORAL = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class RemisionTests(TestCase):
    def setUp(self):
        grupo = Grupo.objects.create(nombre="CABLES Y ALAMBRES")
        self.cable = Material.objects.create(
            codigo="1003100", nombre="CABLE DESNUDO 1/0 CU", grupo=grupo, unidad="MT"
        )
        self.caja = Material.objects.create(
            codigo="2000001", nombre="CAJA", grupo=grupo, unidad="UNIDAD"
        )
        usuario = get_user_model().objects.create_user("jorge", password="x")
        proyecto = Proyecto.objects.create(nombre="Obra de prueba")
        receptor = Empleado.objects.create(nombre="Ana Pérez", cedula="123456")
        self.remision = Remision.objects.create(
            proyecto=proyecto, entregada_por=usuario, recibida_por=receptor
        )

    def test_no_se_repite_material_en_una_remision(self):
        ItemRemision.objects.create(remision=self.remision, material=self.cable, cantidad=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ItemRemision.objects.create(
                    remision=self.remision, material=self.cable, cantidad=2
                )

    def firmar(self, remision):
        remision.firmar(ContentFile(b"png", name="firma.png"), "Ana Pérez", "123456")

    def nueva_remision(self):
        return Remision.objects.create(
            proyecto=self.remision.proyecto,
            entregada_por=self.remision.entregada_por,
            recibida_por=self.remision.recibida_por,
        )

    def test_metros_aceptan_decimales(self):
        ItemRemision.objects.create(
            remision=self.remision, material=self.cable, cantidad=Decimal("12.5")
        )
        self.assertEqual(self.remision.items.count(), 1)

    def test_unidades_no_aceptan_decimales(self):
        with self.assertRaises(ValidationError):
            ItemRemision.objects.create(
                remision=self.remision, material=self.caja, cantidad=Decimal("2.5")
            )

    def test_no_se_puede_firmar_una_remision_vacia(self):
        with self.assertRaises(ValidationError):
            self.firmar(self.remision)

    def test_firmar_asigna_numero_y_cambia_estado(self):
        ItemRemision.objects.create(remision=self.remision, material=self.caja, cantidad=3)
        self.firmar(self.remision)
        self.remision.refresh_from_db()
        self.assertEqual(self.remision.estado, "FIRMADA")
        self.assertEqual(self.remision.numero, 1)
        self.assertIsNotNone(self.remision.firmada_en)

    def test_remision_firmada_no_se_puede_modificar(self):
        ItemRemision.objects.create(remision=self.remision, material=self.caja, cantidad=3)
        self.firmar(self.remision)
        with self.assertRaises(ValidationError):  # no se agregan ítems
            ItemRemision.objects.create(
                remision=self.remision, material=self.cable, cantidad=1
            )
        self.remision.observaciones = "cambio"
        with self.assertRaises(ValidationError):  # no se edita el encabezado
            self.remision.save()

    def test_firmada_se_puede_anular_y_luego_queda_bloqueada(self):
        ItemRemision.objects.create(remision=self.remision, material=self.caja, cantidad=3)
        self.firmar(self.remision)
        self.remision.estado = Remision.Estado.ANULADA
        self.remision.save()
        self.remision.refresh_from_db()
        self.assertEqual(self.remision.estado, "ANULADA")
        self.remision.observaciones = "otro cambio"
        with self.assertRaises(ValidationError):
            self.remision.save()

    def test_numeros_consecutivos(self):
        ItemRemision.objects.create(remision=self.remision, material=self.caja, cantidad=1)
        self.firmar(self.remision)
        otra = self.nueva_remision()
        ItemRemision.objects.create(remision=otra, material=self.caja, cantidad=1)
        self.firmar(otra)
        self.assertEqual(otra.numero, 2)

    def test_borrador_abandonado_no_consume_numero(self):
        self.nueva_remision()  # borrador que nunca se firma
        ItemRemision.objects.create(remision=self.remision, material=self.caja, cantidad=1)
        self.firmar(self.remision)
        self.assertEqual(self.remision.numero, 1)