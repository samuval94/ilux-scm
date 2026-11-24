from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from catalogo.models import Material

PREFERIDOS = ["10001005", "10001006", "609011-1", "609009-1", "10001007", "10007004"]


class Command(BaseCommand):
    help = "Genera un PDF con códigos de barras (Code 128) de materiales reales para probar el escaneo."

    def add_arguments(self, parser):
        parser.add_argument("--cantidad", type=int, default=12)
        parser.add_argument("--salida", default=str(Path(settings.BASE_DIR) / "data" / "codigos_de_prueba.pdf"))

    def handle(self, *args, cantidad, salida, **opts):
        mats = list(Material.objects.filter(codigo__in=PREFERIDOS, activo=True))
        mats += list(Material.objects.filter(activo=True, unidad="MT").exclude(id__in=[m.id for m in mats])[:3])
        mats += list(Material.objects.filter(activo=True).exclude(id__in=[m.id for m in mats])[: max(0, cantidad - len(mats))])
        mats = mats[:cantidad]
        ancho, alto = LETTER
        c = canvas.Canvas(salida, pagesize=LETTER)
        c.setTitle("Códigos de prueba – ILUX SCM")
        por_pagina, y0 = 5, alto - 30 * mm
        for i, m in enumerate(mats):
            pos = i % por_pagina
            if i and pos == 0:
                c.showPage()
            if pos == 0:
                c.setFont("Helvetica-Bold", 14)
                c.drawString(20 * mm, alto - 18 * mm, "ILUX SCM – Códigos de barras de prueba")
                c.setFont("Helvetica", 8)
                c.drawRightString(ancho - 20 * mm, alto - 18 * mm, "Apunta la cámara de la app a cada código")
            y = y0 - pos * 48 * mm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(20 * mm, y, m.nombre[:70])
            c.setFont("Helvetica", 8)
            c.drawString(20 * mm, y - 4.5 * mm, f"{m.codigo} · {m.get_unidad_display()} · {m.get_tipo_display()}")
            b = code128.Code128(m.codigo, barHeight=18 * mm, barWidth=0.55 * mm, humanReadable=False)
            b.drawOn(c, 20 * mm, y - 27 * mm)
            c.setFont("Helvetica", 9)
            c.drawString(20 * mm, y - 32 * mm, m.codigo)
            c.setStrokeGray(0.8)
            c.line(20 * mm, y - 36 * mm, ancho - 20 * mm, y - 36 * mm)
        c.save()
        self.stdout.write(self.style.SUCCESS(f"PDF generado: {salida} ({len(mats)} códigos)"))
