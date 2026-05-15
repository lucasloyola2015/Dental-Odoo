from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicPatientCoverage(models.Model):
    _name = "clinic.patient.coverage"
    _description = "Cobertura de obra social del paciente"
    _inherit = ["mail.thread"]
    _order = "is_primary desc, order, id"
    _rec_name = "display_name"
    _check_company_auto = True

    patient_id = fields.Many2one(
        comodel_name="clinic.patient",
        string="Paciente",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    health_insurance_id = fields.Many2one(
        comodel_name="clinic.health.insurance",
        string="Obra social",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    member_number = fields.Char(string="N° de afiliado", tracking=True)
    plan = fields.Char(string="Plan", help='Nombre del plan específico. Ej: "Plan 310", "Premium".')
    is_holder = fields.Boolean(
        string="Es titular",
        default=True,
        tracking=True,
        help="True si el paciente es el titular directo de la cobertura.",
    )
    holder_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Titular (si no es el paciente)",
        ondelete="restrict",
        help=(
            "Persona titular de la cobertura cuando NO es el paciente "
            "(ej. padre titular de OSDE para hijo menor). Puede no ser paciente de la clínica."
        ),
    )
    os_relationship = fields.Selection(
        selection=[
            ("titular", "Titular"),
            ("spouse", "Cónyuge"),
            ("child", "Hijo / Hija"),
            ("adherent", "Adherente"),
            ("other", "Otro"),
        ],
        string="Parentesco según OS",
        default="titular",
        help="Lo que reconoce la obra social. Por defecto coincide con 'titular'.",
    )
    is_primary = fields.Boolean(
        string="Cobertura principal",
        default=True,
        tracking=True,
        help="Marca la cobertura por defecto al facturar. Solo una por paciente.",
    )
    order = fields.Integer(
        string="Prioridad",
        default=10,
        help="Orden cuando hay múltiples coberturas (FHIR-style: menor = más prioritaria).",
    )
    valid_from = fields.Date(string="Vigente desde", default=fields.Date.context_today, tracking=True)
    valid_to = fields.Date(string="Vigente hasta", tracking=True)
    observations = fields.Text(string="Observaciones")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        index=True,
        related="patient_id.company_id",
        store=True,
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("health_insurance_id", "member_number", "is_primary")
    def _compute_display_name(self):
        for rec in self:
            os = rec.health_insurance_id.name or "?"
            num = rec.member_number or "(sin nº)"
            prefix = "★ " if rec.is_primary else ""
            rec.display_name = f"{prefix}{os} — {num}"

    @api.onchange("is_holder")
    def _onchange_is_holder(self):
        if self.is_holder:
            self.holder_partner_id = False
            self.os_relationship = "titular"

    @api.constrains("is_primary", "patient_id")
    def _check_single_primary(self):
        for rec in self.filtered("is_primary"):
            duplicates = self.search_count([
                ("id", "!=", rec.id),
                ("patient_id", "=", rec.patient_id.id),
                ("is_primary", "=", True),
                ("active", "=", True),
            ])
            if duplicates:
                raise ValidationError(
                    _("El paciente %s ya tiene otra cobertura marcada como principal.") % rec.patient_id.name
                )

    @api.constrains("is_holder", "holder_partner_id")
    def _check_holder_consistency(self):
        for rec in self:
            if not rec.is_holder and not rec.holder_partner_id:
                raise ValidationError(
                    _("Si la cobertura no es titular, hay que indicar quién es el titular.")
                )

    @api.constrains("valid_to", "valid_from")
    def _check_dates(self):
        for rec in self:
            if rec.valid_to and rec.valid_from and rec.valid_to < rec.valid_from:
                raise ValidationError(_("Vigente hasta no puede ser anterior a Vigente desde."))
