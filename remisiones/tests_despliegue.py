import os
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory, TestCase, override_settings


class DetrasDeProxyTests(TestCase):
    @override_settings(SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"))
    def test_con_proxy_las_urls_absolutas_son_https(self):
        req = RequestFactory().get("/", HTTP_HOST="demo.trycloudflare.com", HTTP_X_FORWARDED_PROTO="https")
        self.assertEqual(req.build_absolute_uri("/"), "https://demo.trycloudflare.com/")

    def test_sin_proxy_las_urls_siguen_siendo_http(self):
        req = RequestFactory().get("/", HTTP_HOST="localhost:8000")
        self.assertEqual(req.build_absolute_uri("/"), "http://localhost:8000/")


class FijarClavesTests(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user("admin", password="Ilux2026*")
        User.objects.create_user("almacen", password="Ilux2026*")

    def test_cambia_las_claves(self):
        with mock.patch.dict(os.environ, {"ILUX_CLAVE": "Otra-clave-2026"}):
            call_command("fijar_claves", stdout=StringIO())
        User = get_user_model()
        self.assertTrue(User.objects.get(username="admin").check_password("Otra-clave-2026"))
        self.assertTrue(User.objects.get(username="almacen").check_password("Otra-clave-2026"))

    def test_rechaza_clave_corta_o_de_ejemplo(self):
        for mala in ("corta", "Ilux2026*", "1234567890", "password123"):
            with mock.patch.dict(os.environ, {"ILUX_CLAVE": mala}):
                with self.assertRaises(CommandError):
                    call_command("fijar_claves", stdout=StringIO())
