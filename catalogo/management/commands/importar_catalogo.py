from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalogo.models import Grupo, Material

# Columnas del Excel -> nombres de nuestros campos
COLUMNAS = {
    "sc_detalle_articulo": "nombre",
    "sc_detalle_grupo": "grupo",
    "k_sc_codigo_articulo": "codigo",
    "sc_tipo_unidad": "unidad",
}

# Grupos con el mismo significado y distinto nombre en el Excel
ALIAS_GRUPOS = {"MARCACIONES": "MARCACION"}

# Solo se usan al CREAR un material. Son un borrador conservador: dentro de
# algunos grupos hay mezcla (BROCAS trae también discos y hojas de sierra).
# La base definitiva de Jorge debería traer una columna "tipo".
GRUPOS_HERRAMIENTA = {"HERRAMIENTA MANO", "BROCAS"}
GRUPOS_EQUIPO = {"ACONDICIONADORES UPS Y REGULAD"}


def tipo_por_grupo(grupo):
    if grupo in GRUPOS_HERRAMIENTA:
        return Material.Tipo.HERRAMIENTA
    if grupo in GRUPOS_EQUIPO:
        return Material.Tipo.EQUIPO
    return Material.Tipo.MATERIAL


def leer_archivo(ruta):
    extension = ruta.suffix.lower()
    if extension == ".xls":
        df = pd.read_excel(ruta, engine="xlrd", dtype=str)
    elif extension in (".xlsx", ".xlsm"):
        df = pd.read_excel(ruta, engine="openpyxl", dtype=str)
    elif extension == ".csv":
        df = pd.read_csv(ruta, dtype=str)
    else:
        raise CommandError(f"Formato no soportado: {extension}")

    faltan = [c for c in COLUMNAS if c not in df.columns]
    if faltan:
        raise CommandError(f"Faltan columnas en el archivo: {faltan}")

    columnas = dict(COLUMNAS)
    if "tipo" in df.columns:  # opcional: si la base definitiva la trae, se respeta
        columnas["tipo"] = "tipo"

    df = df[list(columnas)].rename(columns=columnas)
    for c in df.columns:
        df[c] = df[c].fillna("").str.strip()
    return df


class Command(BaseCommand):
    help = "Importa o actualiza el catálogo desde un Excel o CSV (por código)."

    def add_arguments(self, parser):
        parser.add_argument("archivo")
        parser.add_argument(
            "--desactivar-faltantes",
            action="store_true",
            help="Marca como inactivos los materiales que no vienen en el archivo.",
        )

    @transaction.atomic
    def handle(self, *args, archivo, desactivar_faltantes, **opciones):
        ruta = Path(archivo)
        if not ruta.exists():
            raise CommandError(f"No existe el archivo: {ruta}")
        df = leer_archivo(ruta)

        # Validaciones antes de tocar la base de datos
        vacios = df[(df.codigo == "") | (df.nombre == "")]
        if len(vacios):
            raise CommandError(f"Hay {len(vacios)} filas sin código o sin nombre.")
        duplicados = df[df.codigo.duplicated(keep=False)]
        if len(duplicados):
            raise CommandError(f"Códigos duplicados: {sorted(duplicados.codigo.unique())[:10]}")
        desconocidas = set(df.unidad) - set(Material.Unidad.values)
        if desconocidas:
            raise CommandError(f"Unidades desconocidas: {desconocidas}")

        existentes = {m.codigo: m for m in Material.objects.all()}
        grupos = {g.nombre: g for g in Grupo.objects.all()}
        creados = actualizados = 0

        for fila in df.itertuples(index=False):
            nombre_grupo = ALIAS_GRUPOS.get(fila.grupo, fila.grupo)
            if nombre_grupo not in grupos:
                grupos[nombre_grupo] = Grupo.objects.create(nombre=nombre_grupo)
            grupo = grupos[nombre_grupo]
            tipo_archivo = getattr(fila, "tipo", "").upper()

            material = existentes.get(fila.codigo)
            if material is None:
                Material.objects.create(
                    codigo=fila.codigo,
                    nombre=fila.nombre,
                    grupo=grupo,
                    unidad=fila.unidad,
                    tipo=tipo_archivo or tipo_por_grupo(nombre_grupo),
                )
                creados += 1
            else:
                material.nombre = fila.nombre
                material.grupo = grupo
                material.unidad = fila.unidad
                material.activo = True
                if tipo_archivo:  # si el archivo no trae tipo, se respeta el guardado
                    material.tipo = tipo_archivo
                material.save()
                actualizados += 1

        desactivados = 0
        if desactivar_faltantes:
            desactivados = (
                Material.objects.filter(activo=True)
                .exclude(codigo__in=set(df.codigo))
                .update(activo=False)
            )

        self.stdout.write(self.style.SUCCESS(
            f"Catálogo listo: {creados} creados, {actualizados} actualizados, "
            f"{desactivados} desactivados."
        ))