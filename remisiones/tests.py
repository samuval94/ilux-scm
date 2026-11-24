import base64
import io
import shutil
import tempfile
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils import timezone
from openpyxl import load_workbook
from PIL import Image
from rest_framework.test import APIClient

from catalogo.models import Grupo, Material

from .models import Consecutivo, Empleado, ItemRemision, Proyecto, Remision

TMP_MEDIA = tempfile.mkdtemp()


def png_b64():
    buf = io.BytesIO()
    img = Image.new("RGB", (200, 80), "white")
    for x in range(20, 180):
        img.putpixel((x, 40), (0, 0, 0))
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        U = get_user_model()
        cls.admin = U.objects.create_user("adm", password="x", is_staff=True, first_name="Ana")
        cls.op = U.objects.create_user("op", password="x", first_name="Omar")
        g = Grupo.objects.create(nombre="G")
        cls.cable = Material.objects.create(codigo="100", nombre="CABLE 12", grupo=g, unidad="MT")
        cls.tornillo = Material.objects.create(codigo="200", nombre="TORNILLO", grupo=g, unidad="UNIDAD")
        cls.pala = Material.objects.create(codigo="609011-1", nombre="PALA", grupo=g, unidad="UNIDAD", tipo="HERRAMIENTA")
        cls.proy = Proyecto.objects.create(nombre="Proyecto A")
        cls.emp = Empleado.objects.create(nombre="Carlos Pérez", cedula="123")

    def nueva(self, **kw):
        return Remision.objects.create(proyecto=self.proy, entregada_por=self.op, recibida_por=self.emp, **kw)


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class ReglasDeNegocioTests(Base):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def firmada(self):
        r = self.nueva()
        ItemRemision.objects.create(remision=r, material=self.tornillo, cantidad=5)
        r.firmar(ContentFile(b"x", name="f.png"), "Carlos", "123")
        return r

    def test_numero_se_asigna_al_firmar_y_es_consecutivo(self):
        r1, r2 = self.firmada(), self.firmada()
        self.assertEqual((r1.numero, r2.numero), (1, 2))
        self.assertEqual(r1.numero_formato, "000001")
        self.assertIsNone(self.nueva().numero)

    def test_no_se_firma_vacia_ni_sin_nombre(self):
        r = self.nueva()
        with self.assertRaises(ValidationError):
            r.firmar(ContentFile(b"x", name="f.png"), "Carlos", "123")
        ItemRemision.objects.create(remision=r, material=self.tornillo, cantidad=1)
        with self.assertRaises(ValidationError):
            r.firmar(ContentFile(b"x", name="f.png"), "", "")
        self.assertEqual(Consecutivo.objects.count(), 0)

    def test_firmada_es_inmutable(self):
        r = self.firmada()
        r.observaciones = "cambio"
        with self.assertRaises(ValidationError):
            r.save()
        with self.assertRaises(ValidationError):
            ItemRemision.objects.create(remision=r, material=self.cable, cantidad=1)
        with self.assertRaises(ValidationError):
            r.items.first().delete()

    def test_anular_con_motivo_y_luego_inmutable(self):
        r = self.firmada()
        with self.assertRaises(ValidationError):
            r.anular(self.admin, "no")
        r.anular(self.admin, "Se entregó el material equivocado")
        self.assertEqual(r.estado, "ANULADA")
        r.refresh_from_db()
        r.observaciones = "x"
        with self.assertRaises(ValidationError):
            r.save()

    def test_no_se_anula_borrador(self):
        with self.assertRaises(ValidationError):
            self.nueva().anular(self.admin, "motivo largo")

    def test_decimales_solo_en_metros_y_kilos(self):
        r = self.nueva()
        ItemRemision.objects.create(remision=r, material=self.cable, cantidad="12.5")
        with self.assertRaises(ValidationError):
            ItemRemision.objects.create(remision=r, material=self.tornillo, cantidad="1.5")

    def test_cantidad_positiva_y_material_unico(self):
        r = self.nueva()
        with self.assertRaises(ValidationError):
            ItemRemision.objects.create(remision=r, material=self.tornillo, cantidad=0)
        ItemRemision.objects.create(remision=r, material=self.tornillo, cantidad=1)
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError), transaction.atomic():
            ItemRemision.objects.create(remision=r, material=self.tornillo, cantidad=2)


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class ApiRemisionesTests(Base):
    def setUp(self):
        self.c = APIClient()
        self.c.force_authenticate(self.op)

    def payload(self, **kw):
        d = {
            "id": str(uuid.uuid4()), "proyecto": self.proy.id, "recibida_por": self.emp.id, "observaciones": "",
            "items": [{"material": self.cable.id, "cantidad": "12.50"}, {"material": self.tornillo.id, "cantidad": "4"}],
            "firmar": False,
        }
        d.update(kw)
        return d

    def firmar_payload(self, **kw):
        return self.payload(firmar=True, firma={"imagen": png_b64(), "nombre": "", "cedula": ""}, **kw)

    def test_login_y_me(self):
        c = APIClient()
        self.assertEqual(c.post("/api/auth/login/", {"username": "op", "password": "mala"}, format="json").status_code, 400)
        r = c.post("/api/auth/login/", {"username": "op", "password": "x"}, format="json").json()
        self.assertEqual(r["user"]["rol"], "OPERADOR")
        c.credentials(HTTP_AUTHORIZATION="Token " + r["token"])
        self.assertEqual(c.get("/api/auth/me/").json()["username"], "op")
        self.assertEqual(APIClient().get("/api/auth/me/").status_code, 401)

    def test_guardar_borrador_y_editarlo(self):
        p = self.payload()
        r = self.c.post("/api/remisiones/guardar/", p, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["estado"], "BORRADOR")
        p["items"] = [{"material": self.tornillo.id, "cantidad": "9"}]
        r = self.c.post("/api/remisiones/guardar/", p, format="json").json()
        self.assertEqual(len(r["items"]), 1)
        self.assertEqual(Remision.objects.count(), 1)

    def test_guardar_y_firmar_en_un_paso_e_idempotente(self):
        p = self.firmar_payload()
        r = self.c.post("/api/remisiones/guardar/", p, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        d = r.json()
        self.assertEqual((d["estado"], d["numero"]), ("FIRMADA", 1))
        self.assertEqual(d["firma_nombre"], "Carlos Pérez")  # toma el nombre del receptor si no se escribe otro
        r2 = self.c.post("/api/remisiones/guardar/", p, format="json")  # reenvío desde el celular
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["numero"], 1)
        self.assertEqual(Remision.objects.count(), 1)

    def test_firmada_no_se_edita_por_api(self):
        p = self.firmar_payload()
        self.c.post("/api/remisiones/guardar/", p, format="json")
        p2 = dict(p, firmar=False, observaciones="hack")
        p2.pop("firma")
        self.assertEqual(self.c.post("/api/remisiones/guardar/", p2, format="json").status_code, 400)

    def test_validaciones(self):
        malo = self.payload(items=[{"material": self.tornillo.id, "cantidad": "1.5"}])
        r = self.c.post("/api/remisiones/guardar/", malo, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("entero", r.json()["detail"])
        self.assertEqual(self.c.post("/api/remisiones/guardar/", self.payload(items=[]), format="json").status_code, 400)
        dup = self.payload(items=[{"material": self.cable.id, "cantidad": "1"}, {"material": self.cable.id, "cantidad": "2"}])
        self.assertEqual(self.c.post("/api/remisiones/guardar/", dup, format="json").status_code, 400)
        sin_firma = self.payload(firmar=True)
        self.assertEqual(self.c.post("/api/remisiones/guardar/", sin_firma, format="json").status_code, 400)
        firma_mala = self.payload(firmar=True, firma={"imagen": "data:image/png;base64,AAAA"})
        self.assertEqual(self.c.post("/api/remisiones/guardar/", firma_mala, format="json").status_code, 400)
        self.assertEqual(Remision.objects.count(), 0)  # todo o nada

    def test_fallo_a_mitad_no_deja_basura(self):
        p = self.payload(items=[{"material": self.cable.id, "cantidad": "1"}, {"material": self.tornillo.id, "cantidad": "1.5"}])
        self.c.post("/api/remisiones/guardar/", p, format="json")
        self.assertEqual(Remision.objects.count(), 0)

    def test_solo_admin_anula(self):
        d = self.c.post("/api/remisiones/guardar/", self.firmar_payload(), format="json").json()
        self.assertEqual(self.c.post(f"/api/remisiones/{d['id']}/anular/", {"motivo": "Error de digitación"}, format="json").status_code, 403)
        self.c.force_authenticate(self.admin)
        self.assertEqual(self.c.post(f"/api/remisiones/{d['id']}/anular/", {"motivo": "x"}, format="json").status_code, 400)
        r = self.c.post(f"/api/remisiones/{d['id']}/anular/", {"motivo": "Error de digitación"}, format="json")
        self.assertEqual(r.json()["estado"], "ANULADA")

    def test_eliminar_borrador_pero_no_firmada(self):
        b = self.c.post("/api/remisiones/guardar/", self.payload(), format="json").json()
        f = self.c.post("/api/remisiones/guardar/", self.firmar_payload(), format="json").json()
        self.assertEqual(self.c.delete(f"/api/remisiones/{f['id']}/").status_code, 400)
        self.assertEqual(self.c.delete(f"/api/remisiones/{b['id']}/").status_code, 204)

    def test_otro_usuario_no_edita_borrador_ajeno(self):
        p = self.payload()
        self.c.post("/api/remisiones/guardar/", p, format="json")
        otro = get_user_model().objects.create_user("otro", password="x")
        c2 = APIClient()
        c2.force_authenticate(otro)
        self.assertEqual(c2.post("/api/remisiones/guardar/", p, format="json").status_code, 403)

    def test_listado_y_filtros(self):
        self.c.post("/api/remisiones/guardar/", self.firmar_payload(), format="json")
        self.c.post("/api/remisiones/guardar/", self.payload(), format="json")
        self.assertEqual(self.c.get("/api/remisiones/").json()["count"], 2)
        self.assertEqual(self.c.get("/api/remisiones/?estado=FIRMADA").json()["count"], 1)
        self.assertEqual(self.c.get("/api/remisiones/?q=carlos").json()["count"], 2)
        self.assertEqual(self.c.get("/api/remisiones/?q=1").json()["count"], 1)  # por número

    def test_pdf_excel_y_firma(self):
        d = self.c.post("/api/remisiones/guardar/", self.firmar_payload(), format="json").json()
        pdf = self.c.get(f"/api/remisiones/{d['id']}/pdf/")
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        borr = self.c.post("/api/remisiones/guardar/", self.payload(), format="json").json()
        self.assertTrue(self.c.get(f"/api/remisiones/{borr['id']}/pdf/").content.startswith(b"%PDF"))
        x = self.c.get(f"/api/remisiones/{d['id']}/excel/")
        ws = load_workbook(io.BytesIO(x.content)).active
        self.assertEqual(ws.max_row, 3)  # encabezado + 2 ítems
        self.assertEqual(ws["H2"].value, "100")
        self.assertEqual(self.c.get(f"/api/remisiones/{d['id']}/firma/").status_code, 200)
        e = self.c.get("/api/remisiones/exportar/?estado=FIRMADA")
        self.assertEqual(load_workbook(io.BytesIO(e.content)).active.max_row, 3)
        pend = self.c.get("/api/remisiones/exportar/?formato=pendientes")
        self.assertEqual(pend.status_code, 200)

    def test_verificacion_publica(self):
        d = self.c.post("/api/remisiones/guardar/", self.firmar_payload(), format="json").json()
        b = self.c.post("/api/remisiones/guardar/", self.payload(), format="json").json()
        anon = APIClient()
        r = anon.get(f"/api/verificar/{d['id']}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["numero_formato"], "000001")
        self.assertNotIn("cedula", r.content.decode())
        self.assertEqual(anon.get(f"/api/verificar/{b['id']}/").status_code, 404)  # borrador no se verifica
        self.assertEqual(anon.get(f"/api/verificar/{uuid.uuid4()}/").status_code, 404)

    def test_herramientas_y_devoluciones(self):
        manana = (timezone.localdate() - timedelta(days=2)).isoformat()
        p = self.firmar_payload(items=[
            {"material": self.pala.id, "cantidad": "1", "devolver_antes_de": manana},
            {"material": self.tornillo.id, "cantidad": "3", "devolver_antes_de": manana},
        ])
        d = self.c.post("/api/remisiones/guardar/", p, format="json").json()
        pend = self.c.get("/api/herramientas/pendientes/").json()
        self.assertEqual(len(pend), 1)  # el tornillo (material) no se rastrea
        self.assertTrue(pend[0]["vencida"])
        self.assertEqual(self.c.get("/api/resumen/").json()["herramientas_vencidas"], 1)
        item_id = pend[0]["id"]
        self.assertEqual(self.c.post(f"/api/items/{item_id}/devolver/", {}, format="json").status_code, 201)
        self.assertEqual(self.c.post(f"/api/items/{item_id}/devolver/", {}, format="json").status_code, 400)
        self.assertEqual(self.c.get("/api/herramientas/pendientes/").json(), [])
        tornillo_id = [i["id"] for i in d["items"] if i["codigo"] == "200"][0]
        self.assertEqual(self.c.post(f"/api/items/{tornillo_id}/devolver/", {}, format="json").status_code, 400)
        self.assertEqual(self.c.get("/api/herramientas/pendientes/excel/").status_code, 200)

    def test_proyectos_y_empleados_solo_admin_escribe(self):
        self.assertEqual(self.c.post("/api/proyectos/", {"nombre": "X"}, format="json").status_code, 403)
        self.c.force_authenticate(self.admin)
        self.assertEqual(self.c.post("/api/proyectos/", {"nombre": "X"}, format="json").status_code, 201)
        self.assertEqual(self.c.post("/api/empleados/", {"nombre": "Y", "cedula": "999"}, format="json").status_code, 201)
        self.assertEqual(self.c.post("/api/empleados/", {"nombre": "Z", "cedula": "999"}, format="json").status_code, 400)

    def test_resumen(self):
        self.c.post("/api/remisiones/guardar/", self.firmar_payload(), format="json")
        r = self.c.get("/api/resumen/").json()
        self.assertEqual((r["firmadas_total"], r["firmadas_hoy"]), (1, 1))
