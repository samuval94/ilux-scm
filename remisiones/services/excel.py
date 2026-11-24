"""Exportación a Excel (openpyxl) con la identidad de ILUX (ámbar y negro).

Las hojas llevan una Tabla de Excel con nombre fijo y el encabezado en la fila 1, para que Power Automate
pueda usar 'List rows present in a table'. Por eso el diseño no agrega filas encima de la tabla.
"""
from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties
from openpyxl.worksheet.table import Table, TableStyleInfo

AMBAR = PatternFill("solid", fgColor="F3B600")
FUENTE = "Calibri"
TINTA = "1C1B1B"
LINEA = Side(style="thin", color="DDDCD7")
BASE = Border(bottom=LINEA)
CABECERA = Border(bottom=Side(style="medium", color=TINTA))
# Estados con texto y color (el color nunca va solo): (color de letra, fondo)
ESTADOS = {
    "Firmada": ("176B42", "E2F3E9"), "Borrador": ("7A5200", "FFF1C2"), "Anulada": ("A11D13", "FBE6E3"),
    "Sí": ("A11D13", "FBE6E3"),
}
# Columnas de cifras: alineadas a la derecha
NUMEROS = {"Cantidad", "Ítems", "Horas sin firmar", "Días de retraso"}


def _local(dt):
    return timezone.localtime(dt).replace(tzinfo=None) if dt else None


def _hoja(wb, titulo, nombre_tabla, encabezados, filas, anchos=None, formatos=None):
    ws = wb.create_sheet(titulo)
    ws.append(encabezados)
    for f in filas:
        ws.append(f)
    for c in ws[1]:
        c.font = Font(name=FUENTE, bold=True, size=11, color="000000")
        c.fill = AMBAR
        c.border = CABECERA
        c.alignment = Alignment(vertical="center", horizontal="right" if c.value in NUMEROS else "left", indent=1, wrap_text=True)
    ws.row_dimensions[1].height = 28
    for fila in ws.iter_rows(min_row=2):
        ws.row_dimensions[fila[0].row].height = 20
        for c in fila:
            enc = encabezados[c.column - 1]
            c.font = Font(name=FUENTE, size=10.5, color=TINTA)
            c.border = BASE
            c.alignment = Alignment(vertical="center", horizontal="right" if enc in NUMEROS else "left", indent=1)
            if c.value in ESTADOS and enc in ("Estado", "Vencida"):
                letra, fondo = ESTADOS[c.value]
                c.font = Font(name=FUENTE, size=10.5, bold=True, color=letra)
                c.fill = PatternFill("solid", fgColor=fondo)
                c.alignment = Alignment(vertical="center", horizontal="center")
    for i, h in enumerate(encabezados, 1):
        # ancho = el mayor entre el indicado, el del encabezado y el del contenido más largo (tope 60)
        contenido = max((len(str(c.value)) for c in ws[get_column_letter(i)][1:] if c.value is not None), default=0)
        ws.column_dimensions[get_column_letter(i)].width = min(max((anchos or {}).get(h, 0), len(str(h)) + 4, contenido + 4, 12), 60)
    for col, fmt in (formatos or {}).items():
        idx = encabezados.index(col) + 1
        for r in range(2, ws.max_row + 1):
            ws.cell(row=r, column=idx).number_format = fmt
    ws.freeze_panes = "A2"
    ws.sheet_properties.tabColor = "F3B600"
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 100
    # Impresión: horizontal, a lo ancho de una hoja, con el encabezado repetido y pie de ILUX
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.print_title_rows = "1:1"
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.oddFooter.left.text = "ILUX Ingeniería S.A.S. · Sistema de Control de Materiales"
    ws.oddFooter.right.text = "Página &P de &N"
    for lado in (ws.oddFooter.left, ws.oddFooter.right):
        lado.size = 8
        lado.font = f"{FUENTE},Regular"
    if ws.max_row >= 2:  # una tabla de Excel necesita al menos una fila de datos
        tabla = Table(displayName=nombre_tabla, ref=f"A1:{get_column_letter(len(encabezados))}{ws.max_row}")
        tabla.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=False)
        ws.add_table(tabla)
    return ws


def excel_remisiones(remisiones):
    """Una fila por ítem de cada remisión."""
    enc = ["Número", "Estado", "Fecha", "Proyecto", "Entregado por", "Recibido por", "Cédula receptor",
           "Código", "Material", "Unidad", "Cantidad", "Observación ítem", "Devolver antes de", "Observaciones", "ID"]
    filas = []
    for r in remisiones:
        entregada = r.entregada_por.get_full_name() or r.entregada_por.username
        items = list(r.items.select_related("material").order_by("id"))
        for it in items:
            filas.append([
                r.numero_formato or "", r.get_estado_display(), _local(r.firmada_en or r.creada_en),
                r.proyecto.nombre, entregada, r.recibida_por.nombre, r.recibida_por.cedula,
                it.material.codigo, it.material.nombre, it.material.unidad, float(it.cantidad),
                it.observacion, it.devolver_antes_de, r.observaciones, str(r.id),
            ])
    wb = Workbook()
    wb.remove(wb.active)
    _hoja(wb, "Remisiones", "Remisiones", enc, filas,
          anchos={"Material": 48, "Proyecto": 32, "Entregado por": 22, "Recibido por": 24, "Fecha": 18, "ID": 38, "Observaciones": 30},
          formatos={"Fecha": "dd/mm/yyyy hh:mm", "Devolver antes de": "dd/mm/yyyy"})
    return _bytes(wb)


def excel_pendientes_firma(remisiones):
    enc = ["Número", "Proyecto", "Entregado por", "Recibido por", "Creada en", "Horas sin firmar", "Ítems", "ID"]
    ahora = timezone.now()
    filas = []
    for r in remisiones:
        filas.append([
            r.numero_formato or "", r.proyecto.nombre, r.entregada_por.get_full_name() or r.entregada_por.username,
            r.recibida_por.nombre, _local(r.creada_en), round((ahora - r.creada_en).total_seconds() / 3600, 1),
            r.items.count(), str(r.id),
        ])
    wb = Workbook()
    wb.remove(wb.active)
    _hoja(wb, "Remisiones pendientes", "RemisionesPendientes", enc, filas,
          anchos={"Proyecto": 32, "Entregado por": 22, "Recibido por": 24, "Creada en": 18, "ID": 38},
          formatos={"Creada en": "dd/mm/yyyy hh:mm"})
    return _bytes(wb)


def excel_herramientas(items):
    enc = ["Código", "Herramienta / equipo", "Tipo", "Cantidad", "Remisión", "Proyecto", "Recibido por",
           "Entregada el", "Devolver antes de", "Días de retraso", "Vencida"]
    hoy = timezone.localdate()
    filas = []
    for it in items:
        r = it.remision
        retraso = (hoy - it.devolver_antes_de).days if it.devolver_antes_de and it.devolver_antes_de < hoy else 0
        filas.append([
            it.material.codigo, it.material.nombre, it.material.get_tipo_display(), float(it.cantidad),
            r.numero_formato, r.proyecto.nombre, r.recibida_por.nombre, _local(r.firmada_en),
            it.devolver_antes_de, retraso, "Sí" if retraso else "No",
        ])
    wb = Workbook()
    wb.remove(wb.active)
    _hoja(wb, "Herramientas entregadas", "HerramientasEntregadas", enc, filas,
          anchos={"Herramienta / equipo": 44, "Proyecto": 32, "Recibido por": 24, "Entregada el": 18},
          formatos={"Entregada el": "dd/mm/yyyy hh:mm", "Devolver antes de": "dd/mm/yyyy"})
    return _bytes(wb)


def _bytes(wb):
    wb.properties.creator = "ILUX Ingeniería S.A.S."
    wb.properties.title = "Sistema de Control de Materiales (SCM)"
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
