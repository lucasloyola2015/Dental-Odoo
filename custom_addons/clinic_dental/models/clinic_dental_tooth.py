from odoo import api, fields, models


class ClinicDentalTooth(models.Model):
    """Catálogo FDI de piezas dentarias (52 entradas: 32 permanentes + 20 temporales).

    FDI World Dental Federation numbering: cada pieza tiene un código de 2 dígitos
    `QP` donde Q es el cuadrante (1-8) y P la posición desde la línea media (1-8).
    Cuadrantes 1-4 son permanentes; 5-8 son temporales.
    """

    _name = "clinic.dental.tooth"
    _description = "Pieza dentaria (catálogo FDI)"
    _order = "fdi_code"
    _rec_name = "display_name"

    fdi_code = fields.Char(
        string="Código FDI",
        required=True,
        index=True,
        help="Numeración FDI World Dental Federation. Ej: 11 = incisivo central superior derecho.",
    )
    name = fields.Char(string="Nombre", required=True, translate=True)
    arch = fields.Selection(
        selection=[("upper", "Superior"), ("lower", "Inferior")],
        string="Arcada",
        required=True,
    )
    quadrant = fields.Integer(
        string="Cuadrante",
        required=True,
        help="Cuadrante FDI: 1-4 permanentes, 5-8 temporales.",
    )
    position = fields.Integer(
        string="Posición",
        required=True,
        help="Posición desde la línea media (1=incisivo central → 8=tercer molar).",
    )
    dentition = fields.Selection(
        selection=[("permanent", "Permanente"), ("deciduous", "Temporal")],
        string="Dentición",
        required=True,
    )
    tooth_type = fields.Selection(
        selection=[
            ("incisor", "Incisivo"),
            ("canine", "Canino"),
            ("premolar", "Premolar"),
            ("molar", "Molar"),
        ],
        string="Tipo",
        required=True,
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)

    _fdi_code_unique = models.Constraint(
        "unique (fdi_code)",
        "El código FDI debe ser único.",
    )

    @api.depends("fdi_code", "name")
    def _compute_display_name(self):
        for rec in self:
            if rec.fdi_code and rec.name:
                rec.display_name = f"{rec.fdi_code} — {rec.name}"
            else:
                rec.display_name = rec.fdi_code or rec.name or "?"
