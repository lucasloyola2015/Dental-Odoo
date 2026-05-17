"""F1 AOSS filler — overlay text onto the AOSS F1 form template (PDF).

The F1 form is a physical paper format used by AOSS (Asociación Odontológica
San Lorenzo Sud) to bill a treatment session to an Obra Social. Each turno
(appointment) ejecutado generates one F1 — printed on top of the official
PDF template, signed by patient + practitioner, and presented to AOSS.

This module does NOT redraw the form (which would require keeping a visual
clone in QWeb). Instead, it generates a one-page PDF overlay with reportlab
and merges it on top of the official template using pypdf. The template is
shipped under data/pdf_templates/ as a non-data resource.

Coordinates are expressed in the source PDF system (pdfplumber: origin
top-left, y growing downward). Conversion to reportlab (origin bottom-left)
is done in _draw().

Field positions are estimates from text extraction of the template; expect
1-2 cycles of visual adjustment after the first print.
"""
from io import BytesIO

from odoo.tools.misc import file_path

# Field positions in source-PDF coordinates (top-left origin, pt).
# (x, y_top) where y_top is the baseline measured from the top of the page.
# All values calibrated from pdfplumber text extraction; can be tweaked
# without touching the rest of the code.
FIELD_POSITIONS = {
    # ---------- Cabecera principal (cuerpo izquierdo) ----------
    "os_code":          (200, 38),
    "plan":             (305, 38),
    "mes":              (380, 38),
    "anio":             (420, 38),
    "afiliado":         (220, 68),
    "apellido_nombre":  (95,  98),
    "fecha_nac_dia":    (340, 98),
    "fecha_nac_mes":    (358, 98),
    "fecha_nac_anio":   (376, 98),
    "domicilio":        (85,  112),
    "localidad":        (290, 112),
    "documento":        (95,  126),
    "telefono":         (245, 126),
    "odontologo":       (95,  140),
    "matricula":        (275, 140),
    # ---------- Totales (esquina inferior izq.) ----------
    "a_cargo_os":       (130, 410),
    "a_cargo_afil":     (130, 425),
    "total":            (130, 442),
    "presupuesto_n":    (462, 410),
    # ---------- Talón Asociación (centro) ----------
    "asoc_os":          (505, 38),
    "asoc_afiliado":    (505, 68),
    "asoc_mes":         (470, 90),
    "asoc_anio":        (530, 90),
    "asoc_apellido":    (475, 130),
    "asoc_domicilio":   (475, 162),
    "asoc_doc":         (475, 197),
    # ---------- Talón Odontólogo (derecha) ----------
    "odon_os":          (655, 38),
    "odon_afiliado":    (655, 68),
    "odon_mes":         (620, 90),
    "odon_anio":        (680, 90),
    "odon_apellido":    (625, 130),
    "odon_domicilio":   (625, 162),
    "odon_doc":         (625, 197),
}

PAGE_WIDTH = 765.3543
PAGE_HEIGHT = 595.2756
DEFAULT_FONT = "Helvetica"
DEFAULT_SIZE = 9


def _draw(canvas_obj, field, value):
    """Draw a text value at the position for `field`, converting coords to reportlab. """
    if value is None or value == "":
        return
    if field not in FIELD_POSITIONS:
        return
    x, y_top = FIELD_POSITIONS[field]
    # reportlab origin is bottom-left; baseline is the y where text "sits on".
    y_bl = PAGE_HEIGHT - y_top
    canvas_obj.drawString(x, y_bl, str(value))


def render_f1_aoss(data):
    """Generate the filled F1 AOSS PDF bytes.

    :param dict data: keys per FIELD_POSITIONS keys (str values).
    :return bytes: the merged PDF.
    """
    from reportlab.pdfgen import canvas
    # PyPDF2 ships with Odoo 19 globally; pypdf is the newer fork but isn't
    # installed in the service's site-packages by default.
    from PyPDF2 import PdfReader, PdfWriter

    overlay_buf = BytesIO()
    c = canvas.Canvas(overlay_buf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    c.setFont(DEFAULT_FONT, DEFAULT_SIZE)
    for field, value in data.items():
        _draw(c, field, value)
    c.save()
    overlay_buf.seek(0)

    template_path = file_path("clinic_core/data/pdf_templates/F1_AOSS.pdf")
    template = PdfReader(template_path)
    overlay = PdfReader(overlay_buf)
    writer = PdfWriter()
    page = template.pages[0]
    page.merge_page(overlay.pages[0])
    writer.add_page(page)

    out_buf = BytesIO()
    writer.write(out_buf)
    return out_buf.getvalue()
