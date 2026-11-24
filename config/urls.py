import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import include, path, re_path


def spa(request, ruta=""):
    """Sirve el front compilado (React). Cualquier ruta desconocida devuelve index.html."""
    dist = Path(settings.FRONTEND_DIST).resolve()
    if not (dist / "index.html").exists():
        raise Http404(
            "El front no está compilado. Ejecuta: cd frontend && npm install && npm run build "
            "(o usa npm run dev para desarrollo)."
        )
    archivo = (dist / ruta).resolve()
    if ruta and archivo.is_file() and dist in archivo.parents:
        tipo, _ = mimetypes.guess_type(str(archivo))
        resp = FileResponse(open(archivo, "rb"), content_type=tipo or "application/octet-stream")
        if archivo.name in ("sw.js", "index.html", "manifest.webmanifest"):
            resp["Cache-Control"] = "no-cache"
        return resp
    resp = FileResponse(open(dist / "index.html", "rb"), content_type="text/html")
    resp["Cache-Control"] = "no-cache"
    return resp


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("catalogo.urls")),
    path("api/", include("remisiones.urls")),
    re_path(r"^(?!api/|admin/|static/)(?P<ruta>.*)$", spa),
]
