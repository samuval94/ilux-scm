@echo off
REM ILUX SCM - modo demostracion con HTTPS (se usa junto con un tunel de Cloudflare)
REM Paso 1: ejecuta este archivo.  Paso 2: en otra terminal, ejecuta  cloudflared tunnel --url http://localhost:8000
cd /d %~dp0
if not exist venv (
  echo Creando entorno virtual...
  python -m venv venv
)
call venv\Scripts\activate
echo Instalando dependencias...
pip install -q -r requirements.txt
set DJANGO_DEBUG=0
set ILUX_DETRAS_DE_PROXY=1
set DJANGO_ALLOWED_HOSTS=.trycloudflare.com,localhost,127.0.0.1
set DJANGO_CSRF_TRUSTED_ORIGINS=https://*.trycloudflare.com
for /f %%i in ('python -c "import secrets;print(secrets.token_urlsafe(50))"') do set DJANGO_SECRET_KEY=%%i
python manage.py migrate
python manage.py cargar_demo
python manage.py collectstatic --noinput
echo.
echo Elige una clave para los usuarios admin y almacen (minimo 10 caracteres, sin los simbolos & %% ^)
set /p ILUX_CLAVE=Clave: 
python manage.py fijar_claves
if errorlevel 1 (
  echo No se cambio la clave. Vuelve a ejecutar este archivo.
  pause
  exit /b 1
)
echo.
echo ===== App lista en http://localhost:8000 (solo esta laptop). Ahora abre el tunel de Cloudflare. =====
python -m waitress --listen=127.0.0.1:8000 --threads=8 config.wsgi:application
