from odoo import fields, models


class ClinicAppointment(models.Model):
    _inherit = "clinic.appointment"

    tooth_ids = fields.Many2many(
        comodel_name="clinic.dental.tooth",
        relation="clinic_appointment_tooth_rel",
        column1="appointment_id",
        column2="tooth_id",
        string="Piezas dentarias",
        help=(
            "Piezas dentarias atendidas en este turno. Vacío si la práctica "
            "no aplica a piezas específicas (ej. limpieza general, consulta)."
        ),
    )
