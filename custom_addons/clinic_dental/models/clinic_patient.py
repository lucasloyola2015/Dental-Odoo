from odoo import fields, models


class ClinicPatient(models.Model):
    _inherit = "clinic.patient"

    dental_tooth_state_ids = fields.One2many(
        comodel_name="clinic.dental.tooth.state",
        inverse_name="patient_id",
        string="Estado del odontograma",
    )
