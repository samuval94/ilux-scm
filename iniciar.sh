#!/usr/bin/env bash
# ILUX SCM - arranque en un solo paso (Linux / macOS)
cd "$(dirname "$0")"
[ -d venv ] || python3 -m venv venv
. venv/bin/activate
pip install -q -r requirements.txt
python manage.py migrate
python manage.py cargar_demo
echo "===== App lista en http://localhost:8000  (usuario: admin  clave: Ilux2026*) ====="
python manage.py runserver 0.0.0.0:8000
