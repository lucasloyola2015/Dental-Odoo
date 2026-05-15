from odoo import api, fields, models


class ClinicBondSystem(models.Model):
    _name = "clinic.bond.system"
    _description = "Sistema de bonos de una obra social"
    _order = "health_insurance_id, valid_from desc"
    _rec_name = "display_name"

    health_insurance_id = fields.Many2one(
        comodel_name="clinic.health.insurance",
        string="Obra social",
        required=True,
        ondelete="cascade",
        index=True,
    )
    billing_route_id = fields.Many2one(
        comodel_name="clinic.billing.route",
        string="Vía",
        ondelete="restrict",
        help="Vacío = aplica a todas las vías.",
    )
    bond_value = fields.Float(
        string="Valor del bono ($)",
        digits="Product Price",
        required=True,
    )
    format = fields.Selection(
        selection=[
            ("paper", "Papel"),
            ("digital", "Digital"),
            ("mixed", "Mixto (transición)"),
        ],
        string="Formato",
        default="mixed",
        required=True,
    )
    valid_from = fields.Date(string="Vigente desde", required=True, default=fields.Date.context_today)
    observations = fields.Text(string="Observaciones")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("health_insurance_id", "bond_value", "valid_from")
    def _compute_display_name(self):
        for rec in self:
            os = rec.health_insurance_id.code or "?"
            rec.display_name = f"{os} bono ${rec.bond_value:,.2f} (desde {rec.valid_from or '?'})"
