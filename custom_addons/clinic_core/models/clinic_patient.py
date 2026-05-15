from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicPatient(models.Model):
    _name = "clinic.patient"
    _description = "Paciente"
    _inherits = {"res.partner": "partner_id"}
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _check_company_auto = True

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Persona",
        ondelete="cascade",
        required=True,
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    medical_history_number = fields.Char(
        string="N° Historia Clínica",
        tracking=True,
        copy=False,
        index=True,
        readonly=True,
        default=lambda self: _("New"),
        help="Generado automáticamente al crear el paciente. Formato: HC-YYYYNNNN.",
    )
    secretariat_notes = fields.Text(
        string="Notas de secretaría",
        help="Notas operativas (no clínicas). Lo lee el equipo.",
    )
    start_date = fields.Date(
        string="Alta como paciente",
        default=fields.Date.context_today,
        tracking=True,
    )
    end_date = fields.Date(
        string="Baja",
        tracking=True,
    )
    end_reason = fields.Char(
        string="Motivo de baja",
    )
    active = fields.Boolean(default=True, tracking=True)
    coverage_ids = fields.One2many(
        comodel_name="clinic.patient.coverage",
        inverse_name="patient_id",
        string="Coberturas (Obras sociales)",
    )
    appointment_ids = fields.One2many(
        comodel_name="clinic.appointment",
        inverse_name="patient_id",
        string="Turnos",
    )
    appointment_count = fields.Integer(compute="_compute_appointment_count")

    @api.depends("appointment_ids")
    def _compute_appointment_count(self):
        for rec in self:
            rec.appointment_count = len(rec.appointment_ids)

    def action_view_appointments(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("clinic_core.action_clinic_appointment")
        action.update({
            "domain": [("patient_id", "=", self.id)],
            "context": {"default_patient_id": self.id},
        })
        return action

    _hcn_unique_per_company = models.Constraint(
        "unique (medical_history_number, company_id)",
        "El N° de Historia Clínica debe ser único dentro de la compañía.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("partner_id", False)
            if vals.get("partner_id"):
                self.env["res.partner"].browse(vals["partner_id"]).is_clinic_person = True
            # Auto-generate HC number from sequence
            hcn = vals.get("medical_history_number")
            if not hcn or hcn == _("New"):
                seq = self.env["ir.sequence"].next_by_code("clinic.patient.hc")
                vals["medical_history_number"] = seq or "HC-NEW"
        records = super().create(vals_list)
        for rec in records:
            if not rec.partner_id.is_clinic_person:
                rec.partner_id.is_clinic_person = True
        return records

    @api.constrains("end_date", "start_date")
    def _check_dates(self):
        for rec in self:
            if rec.end_date and rec.start_date and rec.end_date < rec.start_date:
                raise ValidationError(_("La fecha de baja no puede ser anterior a la de alta."))

    def action_view_partner(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.partner_id.id,
            "view_mode": "form",
            "target": "current",
        }
