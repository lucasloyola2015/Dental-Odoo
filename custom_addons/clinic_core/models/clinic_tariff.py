from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicTariff(models.Model):
    _name = "clinic.tariff"
    _description = "Tarifario por obra social, vía y práctica"
    _order = "health_insurance_id, billing_route_id, practice_id, valid_from desc"
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
        required=True,
        ondelete="restrict",
        index=True,
    )
    practice_id = fields.Many2one(
        comodel_name="clinic.practice",
        string="Práctica",
        required=True,
        ondelete="cascade",
        index=True,
    )
    amount_paid_by_os = fields.Float(
        string="Paga OS ($)",
        digits="Product Price",
        help="Monto en pesos que paga la obra social al profesional/asociación. Excluyente con bonos.",
    )
    bond_count = fields.Integer(
        string="Bonos",
        help="Cantidad de bonos que cubre la OS. Excluyente con monto en pesos.",
    )
    has_stamp = fields.Boolean(
        string="Lleva estampilla",
        help="True si además del pago/bono requiere estampilla.",
    )
    stamp_value = fields.Float(
        string="Valor estampilla ($)",
        digits="Product Price",
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

    _amount_xor_bonds = models.Constraint(
        "check ((amount_paid_by_os IS NOT NULL AND amount_paid_by_os > 0 AND (bond_count IS NULL OR bond_count = 0)) "
        "OR (bond_count IS NOT NULL AND bond_count > 0 AND (amount_paid_by_os IS NULL OR amount_paid_by_os = 0)))",
        "La tarifa debe especificar OR monto en pesos OR cantidad de bonos, no ambos ni ninguno.",
    )
    _unique_per_validity = models.Constraint(
        "unique (health_insurance_id, billing_route_id, practice_id, valid_from, company_id)",
        "Ya existe una tarifa para esa combinación OS-vía-práctica-fecha en esta compañía.",
    )

    @api.depends("health_insurance_id", "practice_id", "amount_paid_by_os", "bond_count", "valid_from")
    def _compute_display_name(self):
        for rec in self:
            os = rec.health_insurance_id.code or "?"
            prac = rec.practice_id.faco_code or "?"
            if rec.bond_count:
                price = f"{rec.bond_count} bonos"
            else:
                price = f"${rec.amount_paid_by_os:,.2f}" if rec.amount_paid_by_os else "?"
            rec.display_name = f"{os} / {prac} = {price} (desde {rec.valid_from or '?'})"
