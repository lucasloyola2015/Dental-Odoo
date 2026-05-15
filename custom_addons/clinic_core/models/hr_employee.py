from datetime import timedelta

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
    appointment_ids = fields.One2many(
        comodel_name="clinic.appointment",
        inverse_name="practitioner_id",
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
            "domain": [("practitioner_id", "=", self.id)],
            "context": {"default_practitioner_id": self.id},
        })
        return action

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

    def get_resource_calendar_for_company(self, company):
        """Returns the resource.calendar to use for this employee in a given company.

        Lookup order:
        1. The active clinic.practitioner.role.resource_calendar_id for that company.
        2. The employee's own resource_calendar_id (fallback).
        """
        self.ensure_one()
        role = self.env["clinic.practitioner.role"].search([
            ("employee_id", "=", self.id),
            ("company_id", "=", company.id),
            ("active", "=", True),
        ], limit=1)
        if role and role.resource_calendar_id:
            return role.resource_calendar_id
        return self.resource_calendar_id

    def get_available_slots(self, date_from, date_to, duration_minutes, company, practice=None, step_minutes=15):
        """Returns a list of (start_dt, end_dt) tuples where the practitioner is available
        for a `duration_minutes` appointment within [date_from, date_to].

        Algorithm:
        1. Get the resource.calendar for this employee in `company`.
        2. Compute working intervals (respecting leaves).
        3. Subtract existing appointments (non-cancelled, non-noshow, non-errored) with buffer applied.
        4. Slide a window of `duration_minutes` every `step_minutes` and yield those that fit.

        :param date_from: datetime, start of search window (UTC naive)
        :param date_to: datetime, end of search window (UTC naive)
        :param duration_minutes: int, duration of the desired appointment
        :param company: res.company record, the company context
        :param practice: clinic.practice record (optional) — used to refine duration via cascade
        :param step_minutes: granularity of candidate start times (default 15)
        :return: list of (datetime, datetime) tuples
        """
        self.ensure_one()
        if practice:
            duration_minutes = self.get_default_appointment_duration(practice) or duration_minutes

        calendar = self.get_resource_calendar_for_company(company)
        if not calendar:
            return []

        # 1. Working intervals from resource.calendar
        work_intervals_dict = calendar._work_intervals_batch(
            date_from, date_to, resources=self.resource_id,
        )
        work_intervals = list(work_intervals_dict.get(self.resource_id.id, []))

        # 2. Existing appointments in window
        blocking_states = ("pending", "booked", "checked-in", "arrived", "fulfilled")
        existing = self.env["clinic.appointment"].search([
            ("practitioner_id", "=", self.id),
            ("company_id", "=", company.id),
            ("state", "in", blocking_states),
            ("start_datetime", "<", date_to),
            ("end_datetime", ">", date_from),
        ])
        buffer = timedelta(minutes=self.slots_buffer_post_minutes or 0)
        busy = [(appt.start_datetime, appt.end_datetime + buffer) for appt in existing]

        # 3. Slide window
        slot_delta = timedelta(minutes=duration_minutes)
        step_delta = timedelta(minutes=step_minutes)
        available = []
        for wi in work_intervals:
            wi_start, wi_end = wi[0], wi[1]
            candidate = wi_start
            while candidate + slot_delta <= wi_end:
                candidate_end = candidate + slot_delta
                if not any(b_start < candidate_end and b_end > candidate for b_start, b_end in busy):
                    available.append((candidate, candidate_end))
                candidate += step_delta
        return available
