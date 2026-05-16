from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicHealthInsurance(models.Model):
    _name = "clinic.health.insurance"
    _description = "Obra social"
    _order = "name"

    name = fields.Char(string="Nombre", required=True, translate=True)
    code = fields.Char(
        string="Código",
        required=True,
        help="Código corto identificador. Ej: IAPOS, AVALIAN, OSDE.",
    )
    observations = fields.Text(
        string="Observaciones",
        help=(
            "Normas generales de la obra social en texto libre. "
            "Ej: 'Hasta 3 prestaciones por mes incluyendo consulta. Capítulo II y III en menores +10%.'"
        ),
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        index=True,
        help="Vacío = obra social compartida entre todas las compañías (catálogo nacional).",
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
                    _("Ya existe una obra social con el código %s en este alcance.") % rec.code
                )
