from odoo import api, fields, models


class ClinicCopayment(models.Model):
    _name = "clinic.copayment"
    _description = "Copago del paciente para una obra social"
    _order = "health_insurance_id, practice_id, valid_from desc"
    _rec_name = "display_name"

    health_insurance_id = fields.Many2one(
        comodel_name="clinic.health.insurance",
        string="Obra social",
        required=True,
        ondelete="cascade",
        index=True,
    )
    practice_id = fields.Many2one(
        comodel_name="clinic.practice",
        string="Práctica",
        ondelete="cascade",
        help="Vacío = copago aplica a todas las prácticas de la OS.",
    )
    amount = fields.Float(
        string="Copago ($)",
        digits="Product Price",
        required=True,
    )
    valid_from = fields.Date(string="Vigente desde", required=True, default=fields.Date.context_today)
    observations = fields.Text(string="Observaciones")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("health_insurance_id", "practice_id", "amount", "valid_from")
    def _compute_display_name(self):
        for rec in self:
            os = rec.health_insurance_id.code or "?"
            prac = rec.practice_id.faco_code or "TODAS"
            rec.display_name = f"{os} / {prac} copago ${rec.amount:,.2f} (desde {rec.valid_from or '?'})"
