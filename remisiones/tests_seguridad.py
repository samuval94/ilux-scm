from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from remisiones.seguridad import MAX_INTENTOS

CLAVE = "Clave-Buena-2026"


class SesionesTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user("ana", password=CLAVE)
        self.c = APIClient()

    def login(self, clave=CLAVE, usuario="ana"):
        return self.c.post("/api/auth/login/", {"username": usuario, "password": clave}, format="json")

    def test_token_vigente_funciona(self):
        tok = self.login().data["token"]
        self.c.credentials(HTTP_AUTHORIZATION="Token " + tok)
        self.assertEqual(self.c.get("/api/auth/me/").status_code, 200)

    def test_token_vencido_da_401_y_se_borra(self):
        tok = self.login().data["token"]
        Token.objects.filter(key=tok).update(created=timezone.now() - timedelta(hours=13))
        self.c.credentials(HTTP_AUTHORIZATION="Token " + tok)
        r = self.c.get("/api/auth/me/")
        self.assertEqual(r.status_code, 401)
        self.assertFalse(Token.objects.filter(key=tok).exists())

    def test_nuevo_login_reemplaza_el_token_vencido(self):
        viejo = self.login().data["token"]
        Token.objects.filter(key=viejo).update(created=timezone.now() - timedelta(hours=13))
        nuevo = self.login().data["token"]
        self.assertNotEqual(viejo, nuevo)
        self.c.credentials(HTTP_AUTHORIZATION="Token " + nuevo)
        self.assertEqual(self.c.get("/api/auth/me/").status_code, 200)

    def test_login_vigente_conserva_el_mismo_token(self):
        self.assertEqual(self.login().data["token"], self.login().data["token"])

    @override_settings(SESION_HORAS=1)
    def test_la_duracion_es_configurable(self):
        tok = self.login().data["token"]
        Token.objects.filter(key=tok).update(created=timezone.now() - timedelta(hours=2))
        self.c.credentials(HTTP_AUTHORIZATION="Token " + tok)
        self.assertEqual(self.c.get("/api/auth/me/").status_code, 401)


class BloqueoTests(TestCase):
    def setUp(self):
        cache.clear()
        get_user_model().objects.create_user("ana", password=CLAVE)
        self.c = APIClient()

    def intento(self, clave, usuario="ana"):
        return self.c.post("/api/auth/login/", {"username": usuario, "password": clave}, format="json")

    def test_bloquea_tras_los_intentos_fallidos_aun_con_clave_correcta(self):
        for _ in range(MAX_INTENTOS):
            self.assertEqual(self.intento("mala").status_code, 400)
        r = self.intento(CLAVE)
        self.assertEqual(r.status_code, 429)
        self.assertIn("minuto", r.data["detail"])

    def test_un_login_correcto_reinicia_el_conteo(self):
        for _ in range(MAX_INTENTOS - 1):
            self.intento("mala")
        self.assertEqual(self.intento(CLAVE).status_code, 200)
        for _ in range(MAX_INTENTOS - 1):
            self.assertEqual(self.intento("mala").status_code, 400)

    def test_el_bloqueo_es_por_usuario(self):
        for _ in range(MAX_INTENTOS):
            self.intento("mala")
        get_user_model().objects.create_user("luis", password=CLAVE)
        self.assertEqual(self.intento(CLAVE, "luis").status_code, 200)

    def test_usuario_inexistente_tambien_se_bloquea_sin_revelar_si_existe(self):
        for _ in range(MAX_INTENTOS):
            self.assertEqual(self.intento("x", "fantasma").status_code, 400)
        self.assertEqual(self.intento("x", "fantasma").status_code, 429)


class CabecerasTests(TestCase):
    def test_la_app_lleva_csp_y_permisos(self):
        r = self.client.get("/")
        self.assertIn("script-src 'self'", r["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", r["Content-Security-Policy"])
        self.assertIn("camera=(self)", r["Permissions-Policy"])
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")

    def test_el_admin_lleva_csp(self):
        r = self.client.get("/admin/login/")
        self.assertIn("Content-Security-Policy", r)

    def test_la_api_no_se_guarda_en_cache(self):
        r = self.client.get("/api/resumen/")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r["Cache-Control"], "no-store")
