#!/usr/bin/env bash
# ILUX SCM - modo demostración con HTTPS (se usa junto con un túnel de Cloudflare)
# Paso 1: ./demo_https.sh   Paso 2: en otra terminal, cloudflared tunnel --url http://localhost:8000
cd "$(dirname "$0")"
[ -d venv ] || python3 -m venv venv
. venv/bin/activate
pip install -q -r requirements.txt
export DJANGO_DEBUG=0 ILUX_DETRAS_DE_PROXY=1
export DJANGO_ALLOWED_HOSTS=".trycloudflare.com,localhost,127.0.0.1"
export DJANGO_CSRF_TRUSTED_ORIGINS="https://*.trycloudflare.com"
export DJANGO_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(50))')"
python manage.py migrate
python manage.py cargar_demo
python manage.py collectstatic --noinput
read -rsp "Clave para admin y almacén (mínimo 10 caracteres): " ILUX_CLAVE; echo
export ILUX_CLAVE
python manage.py fijar_claves || exit 1
echo "===== App lista en http://localhost:8000 (solo esta máquina). Ahora abre el túnel de Cloudflare. ====="
python -m waitress --listen=127.0.0.1:8000 --threads=8 config.wsgi:application
