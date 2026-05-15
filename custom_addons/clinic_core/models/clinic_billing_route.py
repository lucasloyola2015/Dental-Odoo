from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicBillingRoute(models.Model):
    _name = "clinic.billing.route"
    _description = "Vía de facturación"
    _order = "name"

    name = fields.Char(string="Nombre", required=True, translate=True)
    code = fields.Char(
        string="Código",
        required=True,
        help="Código corto. Ej: DIRECTO, ASOR, AOSS.",
    )
    requires_membership = fields.Boolean(
        string="Requiere ser socio",
        help="True si el profesional debe ser socio de la asociación para usar esta vía.",
    )
    observations = fields.Text(
        string="Observaciones",
        help=(
            "Particularidades de la vía. "
            "Ej: 'ASOR audita prótesis los martes y jueves de 9 a 12hs presencialmente.'"
        ),
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        index=True,
        help="Vacío = vía compartida entre todas las compañías.",
    )

    @api.constrains("code", "company_id")
    def _check_code_unique(self):
        for rec in self:
            domain = [("id", "!=", rec.id), ("code", "=", rec.code)]
            if rec.company_id:
                domain.append(("company_id", "in", (False, rec.company_id.id)))
            else:
                domain.append(("company_id", "=", False))
            if self.with_context(active_test=False).search_count(domain):
                raise ValidationError(
                    _("Ya existe una vía con el código %s en este alcance.") % rec.code
                )
