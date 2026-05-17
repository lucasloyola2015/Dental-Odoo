from odoo import _, api, fields, models


class ClinicBillingRoutePdfField(models.Model):
    """One row per (route, field) defining where to print a data value on the
    route's PDF template. Coordinates are in PDF points with top-left origin
    (the same convention pdfplumber uses for text extraction)."""

    _name = "clinic.billing.route.pdf.field"
    _description = "Campo a sobreimprimir en el formulario de una vía de facturación"
    _order = "billing_route_id, sequence, field_key"

    billing_route_id = fields.Many2one(
        comodel_name="clinic.billing.route",
        string="Vía de facturación",
        required=True,
        ondelete="cascade",
        index=True,
    )
    field_key = fields.Char(
        string="Clave",
        required=True,
        help=(
            "Clave técnica que el código del módulo usa para mapear el dato. "
            "Ej: os_code, apellido_nombre, afiliado, asoc_doc, total."
        ),
    )
    label = fields.Char(
        string="Etiqueta",
        help="Nombre humano del campo. Solo para que la lista sea legible; no afecta el render.",
    )
    x = fields.Float(
        string="X (pt)",
        required=True,
        help="Posición horizontal en puntos PDF. Origen en la esquina superior izquierda.",
    )
    y = fields.Float(
        string="Y (pt)",
        required=True,
        help="Posición vertical en puntos PDF (top-left origin). Aumenta hacia abajo.",
    )
    font_size = fields.Integer(
        string="Tamaño font",
        default=9,
    )
    sequence = fields.Integer(string="Secuencia", default=10)

    _field_key_unique = models.Constraint(
        "unique (billing_route_id, field_key)",
        "La clave de campo debe ser única dentro de la vía de facturación.",
    )
