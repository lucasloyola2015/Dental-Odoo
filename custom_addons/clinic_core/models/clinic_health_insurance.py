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

    # ---- Smart button counts ----
    tariff_count = fields.Integer(
        string="Tarifas", compute="_compute_smart_counts",
    )
    copayment_count = fields.Integer(
        string="Copagos", compute="_compute_smart_counts",
    )
    bond_system_count = fields.Integer(
        string="Sistemas de bonos", compute="_compute_smart_counts",
    )
    practice_code_count = fields.Integer(
        string="Códigos por práctica", compute="_compute_smart_counts",
    )
    insurance_route_count = fields.Integer(
        string="Vías que la aceptan", compute="_compute_smart_counts",
    )

    def _compute_smart_counts(self):
        for rec in self:
            rec.tariff_count = self.env["clinic.tariff"].search_count([
                ("health_insurance_id", "=", rec.id),
            ])
            rec.copayment_count = self.env["clinic.copayment"].search_count([
                ("health_insurance_id", "=", rec.id),
            ])
            rec.bond_system_count = self.env["clinic.bond.system"].search_count([
                ("health_insurance_id", "=", rec.id),
            ])
            rec.practice_code_count = self.env["clinic.practice.code.os"].search_count([
                ("health_insurance_id", "=", rec.id),
            ])
            rec.insurance_route_count = self.env["clinic.insurance.route"].search_count([
                ("health_insurance_id", "=", rec.id),
            ])

    # ---- Smart button actions: open filtered list of the related model ----
    def _open_related(self, model_xmlid, name):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"{name} — {self.name}",
            "res_model": self.env.ref(model_xmlid).res_model,
            "view_mode": "list,form",
            "domain": [("health_insurance_id", "=", self.id)],
            "context": {"default_health_insurance_id": self.id},
        }

    def action_view_tariffs(self):
        return self._open_related("clinic_core.action_clinic_tariff", _("Tarifas"))

    def action_view_copayments(self):
        return self._open_related("clinic_core.action_clinic_copayment", _("Copagos"))

    def action_view_bond_systems(self):
        return self._open_related("clinic_core.action_clinic_bond_system", _("Sistemas de bonos"))

    def action_view_practice_codes(self):
        return self._open_related("clinic_core.action_clinic_practice_code_os", _("Códigos por práctica"))

    def action_view_insurance_routes(self):
        return self._open_related("clinic_core.action_clinic_insurance_route", _("Vías que la aceptan"))

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
