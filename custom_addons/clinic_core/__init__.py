import base64

from . import models
from . import wizards
from . import controllers


# Human-readable labels for the F1 AOSS fields, used by the post_init seed.
# Each key matches a key in tools.f1_aoss_filler.FIELD_POSITIONS.
F1_AOSS_FIELD_LABELS = {
    "os_code":         ("OS (cabecera)", 10),
    "plan":            ("Plan",           20),
    "mes":             ("Mes",            30),
    "anio":            ("Año",            40),
    "afiliado":        ("Nº Afiliado",    50),
    "apellido_nombre": ("Apellido y Nombre", 60),
    "fecha_nac_dia":   ("Fecha nac (día)",   70),
    "fecha_nac_mes":   ("Fecha nac (mes)",   80),
    "fecha_nac_anio":  ("Fecha nac (año)",   90),
    "domicilio":       ("Domicilio",       100),
    "localidad":       ("Localidad",       110),
    "documento":       ("Documento",       120),
    "telefono":        ("Teléfono",        130),
    "odontologo":      ("Odontólogo",      140),
    "matricula":       ("Matrícula",       150),
    "a_cargo_os":      ("A cargo OS",      200),
    "a_cargo_afil":    ("A cargo Afiliado", 210),
    "total":           ("Total",           220),
    "presupuesto_n":   ("Presupuesto Nº",  230),
    "asoc_os":         ("Talón Asoc. — OS", 300),
    "asoc_afiliado":   ("Talón Asoc. — Afiliado", 310),
    "asoc_mes":        ("Talón Asoc. — Mes", 320),
    "asoc_anio":       ("Talón Asoc. — Año", 330),
    "asoc_apellido":   ("Talón Asoc. — Apellido y Nombre", 340),
    "asoc_domicilio":  ("Talón Asoc. — Domicilio", 350),
    "asoc_doc":        ("Talón Asoc. — Documento", 360),
    "odon_os":         ("Talón Odon. — OS", 400),
    "odon_afiliado":   ("Talón Odon. — Afiliado", 410),
    "odon_mes":        ("Talón Odon. — Mes", 420),
    "odon_anio":       ("Talón Odon. — Año", 430),
    "odon_apellido":   ("Talón Odon. — Apellido y Nombre", 440),
    "odon_domicilio":  ("Talón Odon. — Domicilio", 450),
    "odon_doc":        ("Talón Odon. — Documento", 460),
}


def _post_init_hook(env):
    """Seed AOSS billing_route with the F1 PDF template + per-field coords.

    Idempotent: skips fields that already exist; only overwrites pdf_template
    when it's empty so user edits aren't clobbered."""
    from odoo.tools.misc import file_path
    from .tools.f1_aoss_filler import FIELD_POSITIONS

    route = env.ref("clinic_core.billing_route_aoss", raise_if_not_found=False)
    if not route:
        return

    if not route.pdf_template:
        try:
            template_path = file_path("clinic_core/data/pdf_templates/F1_AOSS.pdf")
            with open(template_path, "rb") as fh:
                route.write({
                    "pdf_template": base64.b64encode(fh.read()),
                    "pdf_template_filename": "F1_AOSS.pdf",
                })
        except Exception:
            # If the file isn't where we expect, silently skip; the render
            # helper has a hard-coded fallback that still works.
            pass

    existing_keys = set(route.pdf_field_ids.mapped("field_key"))
    rows = []
    for key, (x, y) in FIELD_POSITIONS.items():
        if key in existing_keys:
            continue
        label, sequence = F1_AOSS_FIELD_LABELS.get(key, (key, 999))
        rows.append({
            "billing_route_id": route.id,
            "field_key": key,
            "label": label,
            "x": x,
            "y": y,
            "font_size": 9,
            "sequence": sequence,
        })
    if rows:
        env["clinic.billing.route.pdf.field"].create(rows)
