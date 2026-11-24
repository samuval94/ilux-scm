@echo off
REM ILUX SCM - arranque en un solo paso (Windows)
cd /d %~dp0
if not exist venv (
  echo Creando entorno virtual...
  python -m venv venv
)
call venv\Scripts\activate
echo Instalando dependencias...
pip install -q -r requirements.txt
python manage.py migrate
python manage.py cargar_demo
echo.
echo ===== App lista en http://localhost:8000  (usuario: admin  clave: Ilux2026*) =====
python manage.py runserver 0.0.0.0:8000
