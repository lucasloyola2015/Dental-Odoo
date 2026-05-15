from datetime import timedelta

import pytz

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
    vat = fields.Char(
        string="DNI",
        related="work_contact_id.vat",
        readonly=False,
        store=True,
        tracking=True,
        help="DNI del profesional. Se sincroniza con su contacto asociado.",
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

    def action_create_clinic_patient(self):
        """Open or create a clinic.patient pointing to this employee's work_contact_id.

        Used when a practitioner (or any employee) wants to be a patient in the
        clinic. Avoids creating a duplicate res.partner by reusing the employee's
        existing partner.
        """
        self.ensure_one()
        if not self.work_contact_id:
            from odoo.exceptions import UserError
            raise UserError(_(
                "Este empleado no tiene 'work_contact_id'. Guardá el empleado primero para que Odoo cree su partner asociado."
            ))
        Patient = self.env["clinic.patient"]
        company = self.env.company
        existing = Patient.with_context(active_test=False).search([
            ("partner_id", "=", self.work_contact_id.id),
            ("company_id", "=", company.id),
        ], limit=1)
        if existing:
            patient = existing
            if not patient.active:
                patient.active = True
        else:
            self.work_contact_id.is_clinic_person = True
            patient = Patient.create({
                "partner_id": self.work_contact_id.id,
                "company_id": company.id,
            })
        return {
            "type": "ir.actions.act_window",
            "name": "Paciente",
            "res_model": "clinic.patient",
            "res_id": patient.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.onchange("specialty_main_id")
    def _onchange_specialty_main_id(self):
        if self.specialty_main_id and self.specialty_main_id not in self.specialty_ids:
            self.specialty_ids = [(4, self.specialty_main_id.id)]

    # -------------------------------------------------------------------------
    # Sync name to work_contact_id (Odoo native does NOT do this automatically)
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for emp in records:
            if emp.work_contact_id and emp.name and emp.work_contact_id.name != emp.name:
                emp.work_contact_id.with_context(_syncing_name=True).name = emp.name
        return records

    def write(self, vals):
        res = super().write(vals)
        if "name" in vals and not self.env.context.get("_syncing_name"):
            for emp in self:
                if emp.work_contact_id and emp.work_contact_id.name != emp.name:
                    emp.work_contact_id.with_context(_syncing_name=True).name = emp.name
        return res

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

        # Make datetimes tz-aware (required by v19 _attendance_intervals_batch).
        # Naive datetimes are interpreted as user's local timezone.
        user_tz = pytz.timezone(self.env.user.tz or "UTC")
        df_aware = user_tz.localize(date_from) if date_from.tzinfo is None else date_from
        dt_aware = user_tz.localize(date_to) if date_to.tzinfo is None else date_to

        # 1. Working intervals from resource.calendar (tz-aware in/out)
        work_intervals_dict = calendar._work_intervals_batch(
            df_aware, dt_aware, resources=self.resource_id,
        )
        work_intervals = list(work_intervals_dict.get(self.resource_id.id, []))

        # Normalize to UTC-naive for internal comparison (Odoo stores Datetime as UTC-naive)
        def to_utc_naive(dt):
            if dt.tzinfo is None:
                return dt
            return dt.astimezone(pytz.UTC).replace(tzinfo=None)

        work_intervals_naive = [(to_utc_naive(wi[0]), to_utc_naive(wi[1])) for wi in work_intervals]
        df_naive = to_utc_naive(df_aware)
        dt_naive = to_utc_naive(dt_aware)

        # 2. Existing appointments in window (Datetime fields are UTC-naive in DB)
        blocking_states = ("pending", "booked", "checked-in", "arrived", "fulfilled")
        existing = self.env["clinic.appointment"].search([
            ("practitioner_id", "=", self.id),
            ("company_id", "=", company.id),
            ("state", "in", blocking_states),
            ("start_datetime", "<", dt_naive),
            ("end_datetime", ">", df_naive),
        ])
        buffer = timedelta(minutes=self.slots_buffer_post_minutes or 0)
        busy = [(appt.start_datetime, appt.end_datetime + buffer) for appt in existing]

        # 3. Slide window (all naive UTC)
        slot_delta = timedelta(minutes=duration_minutes)
        step_delta = timedelta(minutes=step_minutes)
        available = []
        for wi_start, wi_end in work_intervals_naive:
            candidate = wi_start
            while candidate + slot_delta <= wi_end:
                candidate_end = candidate + slot_delta
                if not any(b_start < candidate_end and b_end > candidate for b_start, b_end in busy):
                    available.append((candidate, candidate_end))
                candidate += step_delta
        return available
