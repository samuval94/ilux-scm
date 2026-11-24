"""PDF de la remisión (ReportLab) con la identidad de ILUX: logo, paleta (ámbar y negro) y tipografía Barlow.

Solo cambia la presentación: los datos, el QR de verificación y la firma son los mismos de siempre.
Si las fuentes no se pueden cargar, usa Helvetica y el documento se genera igual.
"""
from io import BytesIO
from pathlib import Path

from django.utils import timezone
from reportlab.graphics import renderPDF  # noqa: F401  (necesario para el widget QR)
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, Image, KeepTogether, PageTemplate, Paragraph, Spacer, Table, TableStyle

ASSETS = Path(__file__).resolve().parent / "assets"
LOGO = ASSETS / "logo-ilux.png"

# Paleta de ILUX (la misma de la aplicación)
AMBAR = colors.HexColor("#F3B600")
TINTA = colors.HexColor("#1C1B1B")
TINTA_3 = colors.HexColor("#66645F")   # texto secundario (5,3:1 sobre blanco)
LINEA = colors.HexColor("#DDDCD7")
FONDO = colors.HexColor("#F3F3F0")
OK, OK_FONDO = colors.HexColor("#176B42"), colors.HexColor("#E2F3E9")
MAL, MAL_FONDO = colors.HexColor("#A11D13"), colors.HexColor("#FBE6E3")
AVISO, AVISO_FONDO = colors.HexColor("#7A5200"), colors.HexColor("#FFF1C2")


def _registrar_fuentes():
    """Barlow (texto) y Barlow Semi Condensed (títulos y cifras). Devuelve los nombres a usar."""
    try:
        for nombre, archivo in (
            ("Barlow", "Barlow-Regular.ttf"), ("Barlow-SemiBold", "Barlow-SemiBold.ttf"),
            ("Barlow-Bold", "Barlow-Bold.ttf"), ("BarlowSC-Bold", "BarlowSemiCondensed-Bold.ttf"),
        ):
            pdfmetrics.registerFont(TTFont(nombre, str(ASSETS / "fonts" / archivo)))
        pdfmetrics.registerFontFamily("Barlow", normal="Barlow", bold="Barlow-Bold", italic="Barlow", boldItalic="Barlow-Bold")
        return {"txt": "Barlow", "semi": "Barlow-SemiBold", "neg": "Barlow-Bold", "tit": "BarlowSC-Bold"}
    except Exception:  # noqa: BLE001 - sin fuentes, el PDF sigue funcionando con Helvetica
        return {"txt": "Helvetica", "semi": "Helvetica-Bold", "neg": "Helvetica-Bold", "tit": "Helvetica-Bold"}


F = _registrar_fuentes()
_GLIFOS = getattr(getattr(pdfmetrics.getFont(F["txt"]), "face", None), "charToGlyph", None)

_base = getSampleStyleSheet()


def _estilo(nombre, **kw):
    kw.setdefault("fontName", F["txt"])
    kw.setdefault("fontSize", 9.5)
    kw.setdefault("leading", 12.5)
    kw.setdefault("textColor", TINTA)
    return ParagraphStyle(nombre, parent=_base["Normal"], **kw)


ST = {
    "normal": _estilo("n"),
    "peq": _estilo("p", fontSize=8, leading=10.5, textColor=TINTA_3),
    "etq": _estilo("e", fontName=F["semi"], fontSize=8, leading=10.5, textColor=TINTA_3),
    "titulo": _estilo("t", fontName=F["tit"], fontSize=24, leading=26),
    "hdr": _estilo("h", fontName=F["neg"], fontSize=8.5, leading=11, textColor=colors.black),
    "hdrd": _estilo("hd", fontName=F["neg"], fontSize=8.5, leading=11, textColor=colors.black, alignment=TA_RIGHT),
    "der": _estilo("d", alignment=TA_RIGHT),
    "valor": _estilo("v", fontSize=10.5, leading=13.5),
}


def _fmt_cantidad(valor):
    s = f"{valor:,.2f}".rstrip("0").rstrip(".")
    return s.replace(",", "X").replace(".", ",").replace("X", ".")  # 1.250,5


def _fecha(dt):
    return timezone.localtime(dt).strftime("%d/%m/%Y %H:%M") if dt else "—"


def _escape(t):
    t = (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if _GLIFOS:  # un carácter que la fuente no tiene se vería como un recuadro
        t = "".join(c if (ord(c) in _GLIFOS or c in "\n\t") else "?" for c in t)
    return t


def _decorar(estado):
    """Encabezado (logo + banda ámbar como en ilux.com.co), pie y marca de agua."""
    def dibujar(canvas, doc):
        canvas.saveState()
        ancho, alto = LETTER
        # Encabezado: logo a la izquierda, nombre del documento a la derecha y banda ámbar
        lw = 42 * mm
        lh = lw * 123 / 411
        try:
            canvas.drawImage(str(LOGO), 18 * mm, alto - 8 * mm - lh, width=lw, height=lh, mask="auto")
        except Exception:  # noqa: BLE001
            canvas.setFillColor(TINTA)
            canvas.setFont(F["tit"], 22)
            canvas.drawString(18 * mm, alto - 18 * mm, "ILUX")
        canvas.setFillColor(TINTA)
        canvas.setFont(F["tit"], 14)
        canvas.drawRightString(ancho - 18 * mm, alto - 13.5 * mm, "Remisión de materiales")
        canvas.setFillColor(TINTA_3)
        canvas.setFont(F["txt"], 8.5)
        canvas.drawRightString(ancho - 18 * mm, alto - 18.5 * mm, "Sistema de Control de Materiales (SCM)")
        canvas.setFillColor(AMBAR)
        canvas.rect(0, alto - 27 * mm, ancho, 3.5 * mm, stroke=0, fill=1)
        # Pie
        canvas.setStrokeColor(LINEA)
        canvas.setLineWidth(0.6)
        canvas.line(18 * mm, 14 * mm, ancho - 18 * mm, 14 * mm)
        canvas.setFillColor(TINTA_3)
        canvas.setFont(F["txt"], 7.5)
        canvas.drawString(18 * mm, 9.5 * mm, f"ILUX Ingeniería S.A.S. · Generado el {_fecha(timezone.now())}")
        canvas.drawRightString(ancho - 18 * mm, 9.5 * mm, f"Página {doc.page}")
        # Marca de agua
        if estado in ("ANULADA", "BORRADOR"):
            canvas.translate(ancho / 2, alto / 2)
            canvas.rotate(35)
            canvas.setFillColor(colors.Color(0.63, 0.11, 0.07, alpha=0.12) if estado == "ANULADA" else colors.Color(0.4, 0.39, 0.37, alpha=0.13))
            canvas.setFont(F["neg"], 96)
            canvas.drawCentredString(0, 0, "ANULADA" if estado == "ANULADA" else "BORRADOR")
        canvas.restoreState()

    return dibujar


def _qr(url, lado=26 * mm):
    w = QrCodeWidget(url)
    x0, y0, x1, y1 = w.getBounds()
    d = Drawing(lado, lado, transform=[lado / (x1 - x0), 0, 0, lado / (y1 - y0), 0, 0])
    d.add(w)
    return d


def _chip_estado(estado):
    """Estado como texto en una pastilla de color (el color nunca va solo)."""
    texto, fg, bg = {
        "FIRMADA": ("Firmada", OK, OK_FONDO),
        "ANULADA": ("Anulada", MAL, MAL_FONDO),
        "BORRADOR": ("Borrador (sin firma)", AVISO, AVISO_FONDO),
    }[estado]
    p = Paragraph(texto, _estilo("chip" + estado, fontName=F["neg"], fontSize=10, leading=12, textColor=fg))
    chip = Table([[p]], colWidths=[pdfmetrics.stringWidth(texto, F["neg"], 10) + 20], hAlign="RIGHT")
    chip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg), ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return chip


def generar_pdf(remision, url_verificacion):
    buf = BytesIO()
    doc = BaseDocTemplate(
        buf, pagesize=LETTER, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=34 * mm, bottomMargin=20 * mm,
        title=f"Remisión {remision.numero_formato or 'borrador'}", author="ILUX Ingeniería S.A.S.",
    )
    ancho = LETTER[0] - 36 * mm
    # Marco sin relleno interno: así el texto, las tablas, el logo y el pie quedan alineados al mismo margen
    marco = Frame(18 * mm, 20 * mm, ancho, LETTER[1] - 34 * mm - 20 * mm, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="remision", frames=[marco], onPage=_decorar(remision.estado))])
    P = lambda t, s="normal": Paragraph(_escape(t), ST[s])
    story = []

    numero = remision.numero_formato or "SIN NÚMERO"
    cab = Table(
        [[Paragraph(f"Remisión No. {_escape(numero)}", ST["titulo"]), _chip_estado(remision.estado)]],
        colWidths=[ancho * 0.66, ancho * 0.34],
    )
    cab.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (0, 0), 0), ("RIGHTPADDING", (1, 0), (1, 0), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story += [cab, Spacer(1, 4 * mm)]

    entregada = remision.entregada_por.get_full_name() or remision.entregada_por.username
    datos = [
        [P("Proyecto", "etq"), P("Fecha", "etq")],
        [P(remision.proyecto.nombre, "valor"), P(_fecha(remision.firmada_en or remision.creada_en), "valor")],
        [P("Entregado por", "etq"), P("Recibido por", "etq")],
        [P(entregada, "valor"), P(f"{remision.recibida_por.nombre} — C.C. {remision.recibida_por.cedula}", "valor")],
    ]
    t = Table(datos, colWidths=[ancho * 0.5, ancho * 0.5])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FONDO), ("BOX", (0, 0), (-1, -1), 0.6, LINEA),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("TOPPADDING", (0, 0), (-1, 0), 7), ("TOPPADDING", (0, 2), (-1, 2), 5), ("BOTTOMPADDING", (0, 3), (-1, 3), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story += [t, Spacer(1, 6 * mm)]

    filas = [[P("#", "hdr"), P("Código", "hdr"), P("Descripción", "hdr"), P("Unidad", "hdr"), P("Cantidad", "hdrd")]]
    items = list(remision.items.select_related("material").order_by("id"))
    for i, it in enumerate(items, 1):
        extra = []
        if it.observacion:
            extra.append(it.observacion)
        if it.devolver_antes_de:
            extra.append(f"Devolver antes del {it.devolver_antes_de.strftime('%d/%m/%Y')}")
        desc_p = Paragraph(
            _escape(it.material.nombre) + (f'<br/><font size="7.5" color="#66645F">{_escape(" · ".join(extra))}</font>' if extra else ""),
            ST["normal"],
        )
        filas.append([P(str(i)), P(it.material.codigo), desc_p, P(it.material.unidad), Paragraph(f"<b>{_fmt_cantidad(it.cantidad)}</b>", ST["der"])])
    tabla = Table(filas, colWidths=[ancho * 0.06, ancho * 0.16, ancho * 0.52, ancho * 0.12, ancho * 0.14], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AMBAR), ("LINEBELOW", (0, 0), (-1, 0), 1.4, TINTA),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, LINEA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [tabla, Spacer(1, 3 * mm), P(f"Total de ítems: {len(items)}", "peq")]

    if remision.observaciones:
        story += [Spacer(1, 4 * mm), P("Observaciones", "etq"), P(remision.observaciones)]
    if remision.estado == "ANULADA":
        quien = remision.anulada_por.get_full_name() or remision.anulada_por.username if remision.anulada_por else ""
        aviso = Table([[Paragraph(
            f"<b>Remisión anulada</b> el {_fecha(remision.anulada_en)} por {_escape(quien)}. "
            f"Motivo: {_escape(remision.motivo_anulacion)}", _estilo("anul", textColor=MAL))]], colWidths=[ancho])
        aviso.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), MAL_FONDO), ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story += [Spacer(1, 4 * mm), aviso]

    # Firma + QR
    if hasattr(remision, "firma"):
        f = remision.firma
        try:
            img = Image(f.imagen.path, width=60 * mm, height=22 * mm, kind="proportional")
        except Exception:  # noqa: BLE001
            img = P("(imagen de firma no disponible)", "peq")
        firma_celda = [img, Paragraph(f"<b>{_escape(f.nombre)}</b><br/>C.C. {_escape(f.cedula)}<br/>Firmado el {_fecha(f.firmada_en)}", ST["peq"])]
    else:
        firma_celda = [Spacer(1, 22 * mm), P("Sin firma de quien recibe", "peq")]
    qr_celda = [_qr(url_verificacion), Paragraph("Escanee para verificar<br/>la remisión", ST["peq"])]
    firma_tabla = Table([[firma_celda, qr_celda]], colWidths=[ancho * 0.7, ancho * 0.3])
    firma_tabla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LINEABOVE", (0, 0), (0, 0), 0.9, TINTA),
        ("TOPPADDING", (0, 0), (0, 0), 3), ("RIGHTPADDING", (0, 0), (0, 0), 20), ("LEFTPADDING", (0, 0), (0, 0), 0),
    ]))
    bloque_firma = [Spacer(1, 10 * mm), P("Firma de quien recibe", "etq"), firma_tabla, Spacer(1, 2 * mm), P(f"ID: {remision.id}", "peq")]
    story.append(KeepTogether(bloque_firma))

    doc.build(story)
    return buf.getvalue()
