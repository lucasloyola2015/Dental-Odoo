from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_clinic_person = fields.Boolean(
        string="Persona Clínica",
        default=False,
        index=True,
        help="Marca este contacto como una persona física manejada por el módulo de clínica.",
    )
    birthdate = fields.Date(
        string="Fecha de Nacimiento",
        tracking=True,
    )
    gender = fields.Selection(
        selection=[
            ("male", "Masculino"),
            ("female", "Femenino"),
            ("non_binary", "No binario"),
            ("prefer_not_to_say", "Prefiere no decir"),
            ("other", "Otro"),
        ],
        string="Género",
        tracking=True,
    )
    clinic_observations = fields.Text(
        string="Observaciones",
        help="Texto libre con información relevante para la atención. Lo lee el equipo clínico.",
    )

    # --- Patients (relations via _inherits) ---
    clinic_patient_ids = fields.One2many(
        comodel_name="clinic.patient",
        inverse_name="partner_id",
        string="Pacientes",
    )
    clinic_patient_count = fields.Integer(compute="_compute_clinic_patient_count")

    # --- Contact channels ---
    clinic_person_contact_ids = fields.One2many(
        comodel_name="clinic.person.contact",
        inverse_name="partner_id",
        string="Canales de contacto",
    )

    # --- Human links (only direction A → B; B → A would be a separate row) ---
    clinic_link_as_a_ids = fields.One2many(
        comodel_name="clinic.person.link",
        inverse_name="partner_a_id",
        string="Vínculos (como A)",
    )
    clinic_link_as_b_ids = fields.One2many(
        comodel_name="clinic.person.link",
        inverse_name="partner_b_id",
        string="Vínculos (como B)",
    )

    @api.depends("clinic_patient_ids")
    def _compute_clinic_patient_count(self):
        for rec in self:
            rec.clinic_patient_count = len(rec.clinic_patient_ids)

    def action_view_clinic_patients(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("clinic_core.action_clinic_patient")
        if self.clinic_patient_count == 1:
            action.update({
                "view_mode": "form",
                "res_id": self.clinic_patient_ids[:1].id,
                "views": [(False, "form")],
            })
        else:
            action.update({
                "domain": [("partner_id", "=", self.id)],
                "context": {"default_partner_id": self.id},
            })
        return action
