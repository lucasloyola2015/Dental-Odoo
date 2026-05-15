from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    is_clinic_practitioner = fields.Boolean(
        string="Profesional clínico",
        default=False,
        index=True,
        tracking=True,
        help="Marca este empleado como profesional que atiende pacientes en la clínica.",
    )
    medical_license = fields.Char(
        string="Matrícula profesional",
        tracking=True,
        help="Número de matrícula provincial o nacional. Ej: 'MP 12345'.",
    )
    default_appointment_duration_minutes = fields.Integer(
        string="Duración default de turno (min)",
        help=(
            "Override personal de la duración por defecto al agendar. "
            "Vacío = usa la duración de la especialidad principal. "
            "Si la especialidad tampoco define, fallback 30 min."
        ),
    )
    slots_buffer_post_minutes = fields.Integer(
        string="Buffer entre turnos (min)",
        default=0,
        help="Minutos de buffer post turno antes de empezar el próximo. 0 = enganche.",
    )
    specialty_main_id = fields.Many2one(
        comodel_name="clinic.specialty",
        string="Especialidad principal",
        tracking=True,
        index=True,
    )
    specialty_ids = fields.Many2many(
        comodel_name="clinic.specialty",
        relation="hr_employee_clinic_specialty_rel",
        column1="employee_id",
        column2="specialty_id",
        string="Todas las especialidades",
        help="Todas las especialidades del profesional (incluye la principal).",
    )
    clinic_observations = fields.Text(
        string="Observaciones clínicas",
        help=(
            "Texto libre con particularidades del profesional. "
            'Ej: "Solo atiende ortodoncia bajo microscopio." "No atiende ancianos por preferencia."'
        ),
    )
    practitioner_role_ids = fields.One2many(
        comodel_name="clinic.practitioner.role",
        inverse_name="employee_id",
        string="Roles por clínica",
    )
    practitioner_practice_ids = fields.One2many(
        comodel_name="clinic.practitioner.practice",
        inverse_name="employee_id",
        string="Prácticas que realiza",
    )

    @api.onchange("specialty_main_id")
    def _onchange_specialty_main_id(self):
        if self.specialty_main_id and self.specialty_main_id not in self.specialty_ids:
            self.specialty_ids = [(4, self.specialty_main_id.id)]

    def get_default_appointment_duration(self, practice=None):
        """Returns the default duration in minutes for a new appointment.

        Cascade (most specific to least):
        1. Per-practice override (clinic.practitioner.practice.default_duration_minutes) if practice given.
        2. Employee's own default (default_appointment_duration_minutes).
        3. Main specialty's default (specialty_main_id.default_appointment_duration_minutes).
        4. System fallback: 30 minutes.
        """
        self.ensure_one()
        if practice:
            practice_id = practice.id if hasattr(practice, "id") else practice
            pp = self.env["clinic.practitioner.practice"].search([
                ("employee_id", "=", self.id),
                ("practice_id", "=", practice_id),
                ("default_duration_minutes", ">", 0),
            ], limit=1)
            if pp:
                return pp.default_duration_minutes
        if self.default_appointment_duration_minutes:
            return self.default_appointment_duration_minutes
        if self.specialty_main_id and self.specialty_main_id.default_appointment_duration_minutes:
            return self.specialty_main_id.default_appointment_duration_minutes
        return 30
