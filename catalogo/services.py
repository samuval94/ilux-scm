"""Importación del catálogo desde Excel/CSV (upsert por código).

Se usa tanto desde el comando `importar_catalogo` como desde la API (pantalla de administración).
"""
from pathlib import Path

import pandas as pd
from django.db import transaction

from .models import Grupo, Material

COLUMNAS = {
    "sc_detalle_articulo": "nombre",
    "sc_detalle_grupo": "grupo",
    "k_sc_codigo_articulo": "codigo",
    "sc_tipo_unidad": "unidad",
}

# Grupos con el mismo significado y distinto nombre en el Excel
ALIAS_GRUPOS = {"MARCACIONES": "MARCACION"}

# Borrador conservador: solo se asigna tipo por grupo cuando el grupo es claro.
# La base definitiva de Jorge debería traer una columna "tipo" (MATERIAL/HERRAMIENTA/EQUIPO).
GRUPOS_HERRAMIENTA = {"HERRAMIENTA MANO", "BROCAS"}
GRUPOS_EQUIPO = {"ACONDICIONADORES UPS Y REGULAD"}


class ErrorImportacion(ValueError):
    pass


def tipo_por_grupo(grupo):
    if grupo in GRUPOS_HERRAMIENTA:
        return Material.Tipo.HERRAMIENTA
    if grupo in GRUPOS_EQUIPO:
        return Material.Tipo.EQUIPO
    return Material.Tipo.MATERIAL


def leer_archivo(origen, nombre=None):
    """origen: ruta (str/Path) o archivo abierto. nombre: nombre original (para saber la extensión)."""
    ext = Path(nombre or str(origen)).suffix.lower()
    try:
        if ext == ".xls":
            df = pd.read_excel(origen, engine="xlrd", dtype=str)
        elif ext in (".xlsx", ".xlsm"):
            df = pd.read_excel(origen, engine="openpyxl", dtype=str)
        elif ext == ".csv":
            df = pd.read_csv(origen, dtype=str)
        else:
            raise ErrorImportacion(f"Formato no soportado: {ext or 'desconocido'} (usa .xls, .xlsx o .csv)")
    except ErrorImportacion:
        raise
    except Exception as exc:  # archivo corrupto, hoja vacía, etc.
        raise ErrorImportacion(f"No se pudo leer el archivo: {exc}") from exc
    faltan = [c for c in COLUMNAS if c not in df.columns]
    if faltan:
        raise ErrorImportacion(f"Faltan columnas en el archivo: {faltan}")
    cols = dict(COLUMNAS)
    if "tipo" in df.columns:  # opcional: si la base definitiva la trae, se respeta
        cols["tipo"] = "tipo"
    df = df[list(cols)].rename(columns=cols)
    for c in df.columns:
        df[c] = df[c].fillna("").astype(str).str.strip()
    return df


@transaction.atomic
def importar(origen, nombre=None, desactivar_faltantes=False):
    df = leer_archivo(origen, nombre)

    vacios = df[(df.codigo == "") | (df.nombre == "")]
    if len(vacios):
        raise ErrorImportacion(f"Hay {len(vacios)} filas sin código o sin nombre.")
    dups = df[df.codigo.duplicated(keep=False)]
    if len(dups):
        raise ErrorImportacion(f"Códigos duplicados: {sorted(dups.codigo.unique())[:10]}")
    invalidas = set(df.unidad) - set(Material.Unidad.values)
    if invalidas:
        raise ErrorImportacion(f"Unidades desconocidas: {sorted(invalidas)}")
    if "tipo" in df.columns:
        malos = set(df.tipo.str.upper()) - set(Material.Tipo.values) - {""}
        if malos:
            raise ErrorImportacion(f"Tipos desconocidos: {sorted(malos)}")

    existentes = {m.codigo: m for m in Material.objects.all()}
    grupos = {g.nombre: g for g in Grupo.objects.all()}
    creados = actualizados = 0

    for fila in df.itertuples(index=False):
        nombre_grupo = ALIAS_GRUPOS.get(fila.grupo, fila.grupo)
        if nombre_grupo not in grupos:
            grupos[nombre_grupo] = Grupo.objects.create(nombre=nombre_grupo)
        grupo = grupos[nombre_grupo]
        tipo_archivo = getattr(fila, "tipo", "").upper()

        m = existentes.get(fila.codigo)
        if m is None:
            Material.objects.create(
                codigo=fila.codigo,
                nombre=fila.nombre,
                grupo=grupo,
                unidad=fila.unidad,
                tipo=tipo_archivo or tipo_por_grupo(nombre_grupo),
            )
            creados += 1
        else:
            m.nombre, m.grupo, m.unidad, m.activo = fila.nombre, grupo, fila.unidad, True
            if tipo_archivo:  # si no viene en el archivo se respeta el tipo ya guardado
                m.tipo = tipo_archivo
            m.save()
            actualizados += 1

    desactivados = 0
    if desactivar_faltantes:
        desactivados = (
            Material.objects.filter(activo=True).exclude(codigo__in=set(df.codigo)).update(activo=False)
        )
    return {"creados": creados, "actualizados": actualizados, "desactivados": desactivados}
