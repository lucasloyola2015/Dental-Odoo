from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicPractitionerRole(models.Model):
    _name = "clinic.practitioner.role"
    _description = "Rol del profesional en una clínica (FHIR PractitionerRole)"
    _inherit = ["mail.thread"]
    _order = "employee_id, company_id"
    _rec_name = "display_name"
    _check_company_auto = True

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Profesional",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
        domain="[('is_clinic_practitioner', '=', True)]",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    resource_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Horario laboral",
        check_company=True,
        help=(
            "Horario laboral del profesional EN ESTA COMPAÑÍA. "
            "Reemplaza al resource_calendar_id del empleado para el cálculo de disponibilidad "
            "cuando el profesional trabaja en varias clínicas."
        ),
    )
    accepted_insurance_ids = fields.Many2many(
        comodel_name="clinic.health.insurance",
        relation="clinic_practitioner_role_insurance_rel",
        column1="role_id",
        column2="insurance_id",
        string="Obras sociales que acepta",
    )
    billing_route_ids = fields.Many2many(
        comodel_name="clinic.billing.route",
        relation="clinic_practitioner_role_route_rel",
        column1="role_id",
        column2="route_id",
        string="Vías de facturación habilitadas",
        help="Vías que el profesional usa en esta compañía (ej. socio AOSS).",
    )
    gcal_calendar_id = fields.Char(
        string="Google Calendar ID",
        help="ID del calendario en Google Calendar para sync (V2).",
    )
    calendar_color = fields.Char(
        string="Color (hex)",
        help="Color para mostrar los turnos del profesional en la vista calendar. Ej: #1f77b4.",
        default="#1f77b4",
    )
    valid_from = fields.Date(string="Vigente desde", default=fields.Date.context_today, tracking=True)
    valid_to = fields.Date(string="Vigente hasta", tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    notes = fields.Text(string="Notas")
    display_name = fields.Char(compute="_compute_display_name", store=True)

    _employee_company_unique = models.Constraint(
        "unique (employee_id, company_id)",
        "El profesional ya tiene un rol asignado en esta compañía. Edítalo o creá una vigencia distinta.",
    )

    @api.depends("employee_id.name", "company_id.name")
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or "?"
            comp = rec.company_id.name or "?"
            rec.display_name = f"{emp} @ {comp}"

    @api.constrains("valid_to", "valid_from")
    def _check_dates(self):
        for rec in self:
            if rec.valid_to and rec.valid_from and rec.valid_to < rec.valid_from:
                raise ValidationError(_("Vigente hasta no puede ser anterior a Vigente desde."))
