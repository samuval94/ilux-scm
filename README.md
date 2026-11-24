# ILUX SCM – Sistema de Control de Materiales (remisiones digitales)

Prototipo del proyecto de Sistemas de Información (EAFIT, 2026-2) para **ILUX Ingeniería S.A.S.**
El técnico escanea el código de barras del material → el sistema muestra el nombre del catálogo → se edita la
cantidad → quien recibe **firma en pantalla** → la remisión queda bloqueada con número consecutivo y se descarga en **PDF** y **Excel**.

Stack: **Django 6 + Django REST Framework** (API) · **React + Vite** (PWA) · SQLite (se puede pasar a PostgreSQL).

---

## 1. Arranque rápido (solo necesitas Python 3.12 o superior)

**Windows:** doble clic en `iniciar.bat` (o ejecútalo desde la terminal).
**Linux / macOS:** `./iniciar.sh`

Eso crea el entorno virtual, instala dependencias, crea la base de datos, carga datos de demostración
(970 materiales del catálogo de ILUX, proyectos y empleados de ejemplo) y levanta el servidor.

> **El catálogo de ILUX no está en este repositorio** (la carpeta `data/` está en `.gitignore` porque es información de la empresa). Antes de arrancar, copia `BASE_DE_DATOS_MATERIAL.xls` en `data/`; si no está, la app arranca con el catálogo vacío y se puede importar después desde *Gestión → Catálogo*.

Abre **http://localhost:8000**

| Usuario | Clave | Rol |
|---|---|---|
| `admin` | `Ilux2026*` | Administrador (anula remisiones, gestiona catálogo, proyectos y empleados) |
| `almacen` | `Ilux2026*` | Operador (crea, firma y consulta remisiones) |

> Cambia estas claves antes de usar la app con datos reales (`python manage.py changepassword admin`).

Paso a paso manual (equivale al script):

```bash
python -m venv venv
venv\Scripts\activate            # Windows   (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
python manage.py migrate
python manage.py cargar_demo
python manage.py runserver
```

El front ya viene compilado en `frontend/dist` y Django lo sirve en `/`. No necesitas Node para probar.

## 1b. Demostración con HTTPS desde cualquier celular (túnel de Cloudflare)

La cámara, la instalación como app y la descarga del PDF funcionan sin avisos solo con HTTPS. Para una reunión o demo,
sin instalar nada en un servidor:

1. Instala el túnel (una sola vez): `winget install --id Cloudflare.cloudflared` y abre una terminal nueva.
2. Terminal 1: ejecuta `demo_https.bat` (en Linux/macOS, `./demo_https.sh`). Pide una clave nueva para `admin` y `almacen`
   (mínimo 10 caracteres; no acepta claves comunes, solo numéricas ni la de ejemplo) y deja la app en `http://localhost:8000`, solo para esa máquina.
3. Terminal 2: `cloudflared tunnel --url http://localhost:8000`. Imprime una dirección `https://xxxx.trycloudflare.com`.
4. Abre esa dirección en el celular. **Descarga el PDF desde esa dirección**: el QR del PDF apunta a la dirección desde la
   que se generó.
5. Al terminar, cierra el túnel con `Ctrl+C`. La dirección cambia cada vez y cualquiera que la tenga ve la pantalla de inicio
   de sesión, por eso se cambia la clave y se cierra el túnel después.

Este modo usa `DJANGO_DEBUG=0`, `ILUX_DETRAS_DE_PROXY=1` (confía en el encabezado `X-Forwarded-Proto` del túnel) y el
servidor `waitress`. Para un despliegue permanente (enero) se usa el mismo mecanismo detrás de Caddy o nginx.

## 1c. Seguridad: lo que ya trae y cómo se configura

- **Sesiones con vencimiento:** el inicio de sesión dura `ILUX_SESION_HORAS` horas (12 por defecto). Al vencer, la app pide
  iniciar sesión de nuevo; las remisiones firmadas sin señal siguen guardadas en el celular y se envían al volver a entrar.
  Para cerrar sesiones a la fuerza: panel `/admin/` → *Tokens* → borrar.
- **Bloqueo por intentos fallidos:** 5 fallos seguidos con el mismo usuario bloquean ese usuario 15 minutos (aunque
  después se escriba la clave correcta). Si bloquean a alguien por error en una demo, reiniciar el servidor lo desbloquea.
  El conteo vive en memoria; con varios procesos en producción hay que moverlo a una base compartida.
- **Claves:** mínimo 10 caracteres, sin claves comunes ni solo numéricas, ni parecidas al nombre de usuario.
- **Cabeceras:** política de contenido (solo recursos propios), cámara permitida solo para esta app, sin caché en `/api/`,
  protección contra incrustación (clickjacking) y HSTS cuando va detrás de HTTPS (`ILUX_HSTS_SEGUNDOS`).
- **Pendiente para producción:** usuario por persona, auditoría de accesos, copias de seguridad, PostgreSQL y política de datos
  personales (Ley 1581 de 2012). `react-router-dom` 6 tiene un aviso de redirección abierta que no aplica aquí (la app solo
  navega a rutas internas fijas); se resuelve al migrar a la versión 7.

## 2. Cómo probarla (recorrido de 5 minutos)

1. Entra como `almacen`. Elige **proyecto** y **quién recibe**.
2. Agrega ítems de tres formas:
   - **Cámara:** botón *Escanear*. Imprime o abre `data/codigos_de_prueba.pdf` en otra pantalla y apunta la cámara.
   - **Lector USB/Bluetooth:** el campo de código siempre está listo; el lector escribe el código y pulsa Enter.
   - **A mano / por nombre:** escribe `10001005` o `alambre thhn` y elige de la lista (sirve para herramientas sin código impreso).
3. Edita las cantidades. Metros y kilogramos aceptan decimales (`125,5`); las demás unidades solo enteros.
4. **Firmar remisión** → quien recibe firma con el dedo o el mouse → *Firmar y guardar*. Se asigna el número y queda bloqueada.
5. Descarga el **PDF** (con QR de verificación) y el **Excel**.
6. **Historial:** filtros, detalle, firma. Como `admin`, abre una remisión firmada y pulsa **Anular** (pide motivo).
7. **Herramientas:** las herramientas/equipos entregados quedan en seguimiento hasta registrar su devolución
   (en `Gestión → Catálogo` puedes cambiar el *tipo* de cualquier ítem; `PALA` y `MUELA` ya vienen como herramienta).
8. **Sin señal:** en el navegador activa modo avión (o *Offline* en DevTools), firma una remisión → queda en *Pendientes* y se envía sola al volver la conexión.
9. **Panel:** indicadores (remisiones firmadas, % con firma – KPI 2 de la Entrega 2, borradores >24 h, herramientas vencidas).
10. Escanea el **QR del PDF** con el celular: abre la página pública de verificación (`/verificar/<id>`).

### Probar en el celular (cámara)
Los navegadores solo dejan usar la cámara con **HTTPS o localhost**. Para el celular:

```bash
# terminal 1 (en la carpeta del proyecto)
python manage.py runserver 0.0.0.0:8000
# terminal 2
cd frontend
npm install
npm run dev:https
```
En el celular (misma red Wi-Fi) abre `https://IP-DE-TU-PC:5173`, acepta el aviso del certificado de desarrollo y listo.
(Sin HTTPS puedes usar lector USB/Bluetooth o escribir el código.)

## 3. Pruebas automáticas

```bash
python manage.py test        # 50 pruebas: reglas de negocio, API, PDF/Excel, importador, permisos, sesiones, bloqueo y cabeceras
```

## 4. Estructura

```
config/        Configuración de Django y rutas (sirve el front en "/")
catalogo/      Grupos y materiales (material/herramienta/equipo), importador Excel/CSV, API de catálogo
remisiones/    Remisión, ítems, firma, consecutivo, devoluciones; API, PDF (ReportLab) y Excel (openpyxl)
frontend/      React + Vite (PWA). Código fuente en frontend/src, compilado en frontend/dist
data/          BASE_DE_DATOS_MATERIAL.xls (catálogo de ILUX) y codigos_de_prueba.pdf
```

Comandos útiles:

```bash
python manage.py importar_catalogo data/BASE_DE_DATOS_MATERIAL.xls            # crea/actualiza por código
python manage.py importar_catalogo nueva_base.xlsx --desactivar-faltantes      # base definitiva de Jorge
python manage.py codigos_prueba                                                # regenera el PDF de códigos de prueba
python manage.py createsuperuser                                               # más administradores
```
Admin de Django (datos crudos): http://localhost:8000/admin/

Cambiar el front: `cd frontend && npm install && npm run dev` (http://localhost:5173, con proxy al servidor Django) y `npm run build` para compilar.
El diseño (logo, paleta de ILUX, tipografías incluidas en la app, accesibilidad y gráficos del panel) está documentado en `frontend/DISENO.md`.

## 5. Reglas de negocio implementadas (en el modelo, no solo en la pantalla)

- La **solicitud** de materiales no se digitaliza: el flujo parte del escaneo. La app **no maneja precios**.
- Una remisión es siempre completa (sin entregas parciales).
- Estados: `BORRADOR → FIRMADA → ANULADA`. Una **firmada se bloquea**; solo se puede **anular con motivo** (solo administrador). Un borrador se elimina.
- El **número consecutivo** se asigna al firmar (sin huecos, con bloqueo de fila).
- Firma obligatoria con nombre y cédula; se guarda imagen, fecha e IP. Las firmas **no se sirven públicamente** (solo por la API autenticada).
- Cantidad > 0; **decimales solo en metros (MT) y kilogramos (KG)**; un material no se repite en la misma remisión.
- El `id` de la remisión es un UUID creado por el cliente: reenviar la misma remisión no la duplica (modo sin conexión).
- El importador actualiza por **código (texto)**, nunca borra y valida duplicados, unidades y columnas.

## 6. API (resumen)

Autenticación por token: `POST /api/auth/login/` → `Authorization: Token <token>`.

| Ruta | Descripción |
|---|---|
| `GET /api/materiales/?search=&tipo=` · `/catalogo/` · `/por-codigo/<codigo>/` | Catálogo (el completo se guarda en el celular) |
| `POST /api/remisiones/guardar/` | Crea/actualiza un borrador y opcionalmente lo firma (idempotente por UUID) |
| `GET /api/remisiones/?estado=&proyecto=&q=&desde=&hasta=` | Historial con filtros |
| `GET /api/remisiones/<id>/pdf/` · `/excel/` · `/firma/` | Descargas |
| `POST /api/remisiones/<id>/anular/` | Anular con motivo (admin) |
| `GET /api/remisiones/exportar/` | Excel de varias remisiones; `?formato=pendientes` = borradores sin firmar |
| `GET /api/herramientas/pendientes/` · `/excel/` · `POST /api/items/<id>/devolver/` | Seguimiento de devoluciones |
| `GET /api/resumen/` | Indicadores del panel |
| `GET /api/verificar/<id>/` | Verificación pública (destino del QR) |

Los Excel traen una **Tabla de Excel con nombre fijo** (`Remisiones`, `RemisionesPendientes`, `HerramientasEntregadas`) para usarlos con
*Power Automate → Excel Online → "List rows present in a table"* (automatizaciones de la Entrega 3).

## 7. Qué falta / límites conocidos (para decidir con ILUX)

- **Catálogo definitivo:** solo los materiales traen código impreso. Herramientas y equipos se buscan por nombre; el tipo (material/herramienta/equipo) se clasifica en *Gestión → Catálogo* o con la columna `tipo` en la base definitiva.
- **Modo sin conexión:** funciona para crear y firmar (catálogo, proyectos y empleados quedan en el celular; las remisiones firmadas se encolan). No hay PDF hasta que se sincronice.
- Los tokens no vencen (se invalidan al cerrar sesión). Para producción: HTTPS, `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` propia, `DJANGO_ALLOWED_HOSTS`, PostgreSQL y copias de seguridad de `media/` (firmas).
- No incluye: firma remota del receptor desde su propio celular por QR, devoluciones parciales, reportes por proyecto ni integración directa con SAG/Odoo (ver trabajo futuro en la Entrega 3).
