"""Configuración del proyecto ILUX SCM (Sistema de Control de Materiales)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "django-insecure-solo-para-desarrollo-cambiar-en-produccion"
)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
# En desarrollo se acepta cualquier host para poder probar desde el celular en la misma red.
ALLOWED_HOSTS = ["*"] if DEBUG else os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "catalogo",
    "remisiones",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # sirve /static/ (admin) sin depender de runserver
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "remisiones.seguridad.CabecerasSeguridad",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_ROOT.mkdir(exist_ok=True)  # evita el aviso de whitenoise antes del primer collectstatic
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Las firmas se guardan aquí y NO se sirven públicamente: solo por la API autenticada.
MEDIA_ROOT = BASE_DIR / "media"

# Carpeta del front compilado (npm run build). Django lo sirve en "/".
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

# Detrás de un túnel o proxy HTTPS (Cloudflare, Caddy, nginx): el proxy termina el HTTPS y avisa con
# X-Forwarded-Proto. Sin esto, el QR del PDF y el inicio de sesión del admin usarían http://.
DETRAS_DE_PROXY = os.environ.get("ILUX_DETRAS_DE_PROXY", "0") == "1"
if DETRAS_DE_PROXY:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("ILUX_HSTS_SEGUNDOS", "86400"))  # 1 día; súbelo cuando el dominio sea definitivo
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]

# Horas que dura una sesión (el token vence aunque se siga usando). Al vencer, el celular pide iniciar sesión de nuevo;
# las remisiones firmadas sin señal siguen guardadas en el celular y se envían al volver a entrar.
SESION_HORAS = int(os.environ.get("ILUX_SESION_HORAS", "12"))

# Si se define, el QR del PDF apunta a este dominio (ej. https://scm.ilux.com.co).
URL_PUBLICA = os.environ.get("ILUX_URL_PUBLICA", "")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["remisiones.seguridad.TokenConVencimiento"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "EXCEPTION_HANDLER": "remisiones.api_errors.manejador",
}
