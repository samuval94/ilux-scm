import io

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Grupo, Material
from .services import ErrorImportacion, importar


def csv_bytes(filas, encabezado="sc_detalle_articulo,sc_detalle_grupo,k_sc_codigo_articulo,sc_tipo_unidad"):
    return io.BytesIO((encabezado + "\n" + "\n".join(filas) + "\n").encode("utf-8"))


class ImportadorTests(TestCase):
    def test_crea_y_actualiza_por_codigo(self):
        r = importar(csv_bytes(["CABLE 12,CABLES Y ALAMBRES,100,MT", "TOMA,TOMAS E INTERRUPTORES,609009-1,UNIDAD"]), "a.csv")
        self.assertEqual(r["creados"], 2)
        r = importar(csv_bytes(["CABLE 12 AWG,CABLES Y ALAMBRES,100,MT"]), "a.csv")
        self.assertEqual((r["creados"], r["actualizados"]), (0, 1))
        self.assertEqual(Material.objects.get(codigo="100").nombre, "CABLE 12 AWG")
        self.assertEqual(Material.objects.count(), 2)  # nunca se borra

    def test_codigo_texto_se_conserva(self):
        importar(csv_bytes(["MUELA,HERRAMIENTA MANO,609009-1,UNIDAD", "PUNTA,VARIOS,H00001002,UNIDAD"]), "a.csv")
        self.assertTrue(Material.objects.filter(codigo="609009-1", tipo="HERRAMIENTA").exists())
        self.assertTrue(Material.objects.filter(codigo="H00001002").exists())

    def test_alias_de_grupo(self):
        importar(csv_bytes(["ROTULO,MARCACIONES,1,UNIDAD"]), "a.csv")
        self.assertEqual(Material.objects.get().grupo.nombre, "MARCACION")

    def test_desactivar_faltantes(self):
        importar(csv_bytes(["A,G,1,UNIDAD", "B,G,2,UNIDAD"]), "a.csv")
        r = importar(csv_bytes(["A,G,1,UNIDAD"]), "a.csv", desactivar_faltantes=True)
        self.assertEqual(r["desactivados"], 1)
        self.assertFalse(Material.objects.get(codigo="2").activo)

    def test_rechaza_duplicados_unidades_y_columnas(self):
        with self.assertRaises(ErrorImportacion):
            importar(csv_bytes(["A,G,1,UNIDAD", "B,G,1,UNIDAD"]), "a.csv")
        with self.assertRaises(ErrorImportacion):
            importar(csv_bytes(["A,G,1,GALON"]), "a.csv")
        with self.assertRaises(ErrorImportacion):
            importar(csv_bytes(["A,G,1"], encabezado="x,y,z"), "a.csv")
        self.assertEqual(Material.objects.count(), 0)  # transacción: nada a medias

    def test_respeta_columna_tipo(self):
        enc = "sc_detalle_articulo,sc_detalle_grupo,k_sc_codigo_articulo,sc_tipo_unidad,tipo"
        importar(csv_bytes(["TALADRO,VARIOS,5,UNIDAD,EQUIPO"], encabezado=enc), "a.csv")
        self.assertEqual(Material.objects.get().tipo, "EQUIPO")


class MaterialModelTests(TestCase):
    def test_admite_decimales_solo_mt_y_kg(self):
        g = Grupo.objects.create(nombre="G")
        mt = Material.objects.create(codigo="1", nombre="A", grupo=g, unidad="MT")
        kg = Material.objects.create(codigo="2", nombre="B", grupo=g, unidad="KG")
        un = Material.objects.create(codigo="3", nombre="C", grupo=g, unidad="UNIDAD")
        self.assertTrue(mt.admite_decimales and kg.admite_decimales)
        self.assertFalse(un.admite_decimales)


class CatalogoApiTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.admin = U.objects.create_user("adm", password="x", is_staff=True)
        self.op = U.objects.create_user("op", password="x")
        g = Grupo.objects.create(nombre="CABLES")
        self.m = Material.objects.create(codigo="609009-1", nombre="CABLE UTP", grupo=g, unidad="MT")
        Material.objects.create(codigo="2", nombre="INACTIVO", grupo=g, unidad="UNIDAD", activo=False)
        self.c = APIClient()

    def test_requiere_login(self):
        self.assertEqual(self.c.get("/api/materiales/").status_code, 401)

    def test_lista_busqueda_y_catalogo_completo(self):
        self.c.force_authenticate(self.op)
        r = self.c.get("/api/materiales/?search=utp").json()
        self.assertEqual(r["count"], 1)
        self.assertEqual(len(self.c.get("/api/materiales/catalogo/").json()), 1)  # solo activos

    def test_por_codigo(self):
        self.c.force_authenticate(self.op)
        self.assertEqual(self.c.get("/api/materiales/por-codigo/609009-1/").json()["nombre"], "CABLE UTP")
        self.assertEqual(self.c.get("/api/materiales/por-codigo/999/").status_code, 404)
        self.assertEqual(self.c.get("/api/materiales/por-codigo/2/").status_code, 400)

    def test_solo_admin_escribe(self):
        self.c.force_authenticate(self.op)
        self.assertEqual(self.c.post("/api/materiales/", {"codigo": "T1", "nombre": "TALADRO", "unidad": "UNIDAD", "tipo": "EQUIPO"}).status_code, 403)
        self.c.force_authenticate(self.admin)
        r = self.c.post("/api/materiales/", {"codigo": "T1", "nombre": "taladro", "unidad": "UNIDAD", "tipo": "EQUIPO", "grupo_nombre": "equipos"})
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["nombre"], "TALADRO")
        r = self.c.patch(f"/api/materiales/{self.m.id}/", {"tipo": "HERRAMIENTA"})
        self.assertEqual(r.json()["tipo"], "HERRAMIENTA")

    def test_importar_por_api(self):
        self.c.force_authenticate(self.admin)
        f = csv_bytes(["NUEVO,G,77,UNIDAD"])
        f.name = "n.csv"
        r = self.c.post("/api/catalogo/importar/", {"archivo": f}, format="multipart")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["creados"], 1)
