from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ClinicAppointmentWizard(models.TransientModel):
    _name = "clinic.appointment.wizard"
    _description = "Buscar disponibilidad y agendar turno"

    # -------------------------------------------------------------------------
    # Inputs
    # -------------------------------------------------------------------------
    patient_id = fields.Many2one(
        comodel_name="clinic.patient",
        string="Paciente",
        required=True,
    )
    practitioner_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Profesional",
        required=True,
        domain="[('is_clinic_practitioner', '=', True)]",
    )
    practice_id = fields.Many2one(
        comodel_name="clinic.practice",
        string="Práctica",
        help="Si la indicás, ajusta automáticamente la duración del turno.",
    )
    coverage_id = fields.Many2one(
        comodel_name="clinic.patient.coverage",
        string="Cobertura",
        domain="[('patient_id', '=', patient_id)]",
    )
    billing_route_id = fields.Many2one(
        comodel_name="clinic.billing.route",
        string="Vía de facturación",
    )
    duration_minutes = fields.Integer(
        string="Duración (min)",
        compute="_compute_duration_minutes",
        store=True,
        readonly=False,
        help="Calculado por cascada: práctica del profesional → profesional → especialidad → 30 min.",
    )
    date_from = fields.Date(
        string="Desde",
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string="Hasta",
        required=True,
        default=lambda self: fields.Date.context_today(self) + timedelta(days=7),
    )
    step_minutes = fields.Integer(
        string="Granularidad (min)",
        default=15,
        help="Paso entre candidatos. 15 = se prueba cada cuarto de hora.",
    )
    is_overbooking = fields.Boolean(
        string="Sobreturno",
        help="Si está marcado, el turno final se carga como sobreturno (no validar superposición).",
    )
    appointment_reason = fields.Text(string="Motivo de consulta")
    location_id = fields.Many2one(
        comodel_name="clinic.location",
        string="Sucursal",
        required=True,
        default=lambda self: self._default_location_id(),
        help="Sede física donde se va a buscar disponibilidad y crear el turno.",
    )

    @api.model
    def _default_location_id(self):
        return self.env["clinic.location"].search([
            ("company_id", "=", self.env.company.id),
            ("active", "=", True),
        ], limit=1).id or False

    # -------------------------------------------------------------------------
    # Output / state
    # -------------------------------------------------------------------------
    state = fields.Selection(
        selection=[("draft", "Configurar"), ("searched", "Resultados")],
        default="draft",
        required=True,
    )
    slot_ids = fields.One2many(
        comodel_name="clinic.appointment.wizard.slot",
        inverse_name="wizard_id",
        string="Huecos disponibles",
    )
    slot_count = fields.Integer(compute="_compute_slot_count")
    search_message = fields.Char(compute="_compute_slot_count")

    # -------------------------------------------------------------------------
    # Computes
    # -------------------------------------------------------------------------
    @api.depends("practitioner_id", "practice_id")
    def _compute_duration_minutes(self):
        for rec in self:
            if rec.practitioner_id:
                rec.duration_minutes = rec.practitioner_id.get_default_appointment_duration(rec.practice_id)
            else:
                rec.duration_minutes = 30

    @api.depends("slot_ids")
    def _compute_slot_count(self):
        for rec in self:
            count = len(rec.slot_ids)
            rec.slot_count = count
            if rec.state == "draft":
                rec.search_message = ""
            elif count == 0:
                rec.search_message = "Sin huecos disponibles en el rango. Probá ampliar las fechas o cambiar la duración."
            else:
                rec.search_message = f"Se encontraron {count} huecos disponibles."

    @api.onchange("patient_id")
    def _onchange_patient_set_coverage(self):
        if self.patient_id:
            primary = self.patient_id.coverage_ids.filtered(lambda c: c.is_primary and c.active)
            if primary:
                self.coverage_id = primary[0]
            else:
                self.coverage_id = False
        else:
            self.coverage_id = False

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_search_slots(self):
        self.ensure_one()
        if not self.practitioner_id or not self.date_from or not self.date_to:
            raise UserError(_("Cargá profesional y rango de fechas antes de buscar."))
        if self.date_to < self.date_from:
            raise UserError(_("'Hasta' no puede ser anterior a 'Desde'."))
        if self.duration_minutes <= 0:
            raise UserError(_("La duración tiene que ser mayor a cero."))

        # Clear previous results
        self.slot_ids.unlink()

        # Compute search window in datetime (start of date_from to end of date_to)
        date_from_dt = datetime.combine(self.date_from, time.min)
        date_to_dt = datetime.combine(self.date_to + timedelta(days=1), time.min)

        # Call helper on hr.employee
        available = self.practitioner_id.get_available_slots(
            date_from=date_from_dt,
            date_to=date_to_dt,
            duration_minutes=self.duration_minutes,
            location=self.location_id,
            practice=self.practice_id or None,
            step_minutes=self.step_minutes or 15,
        )

        # Cap results to avoid UI overload
        MAX_RESULTS = 200
        if len(available) > MAX_RESULTS:
            available = available[:MAX_RESULTS]

        Slot = self.env["clinic.appointment.wizard.slot"]
        Slot.create([
            {
                "wizard_id": self.id,
                "start_datetime": start,
                "end_datetime": end,
            }
            for start, end in available
        ])

        self.state = "searched"
        return {
            "type": "ir.actions.act_window",
            "res_model": "clinic.appointment.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": dict(self.env.context),
        }

    def action_back_to_inputs(self):
        self.ensure_one()
        self.slot_ids.unlink()
        self.state = "draft"
        return {
            "type": "ir.actions.act_window",
            "res_model": "clinic.appointment.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": dict(self.env.context),
        }


class ClinicAppointmentWizardSlot(models.TransientModel):
    _name = "clinic.appointment.wizard.slot"
    _description = "Hueco disponible (resultado del wizard)"
    _order = "start_datetime"
    _rec_name = "display_name"

    wizard_id = fields.Many2one(
        comodel_name="clinic.appointment.wizard",
        required=True,
        ondelete="cascade",
        index=True,
    )
    start_datetime = fields.Datetime(string="Inicio", required=True)
    end_datetime = fields.Datetime(string="Fin", required=True)
    display_name = fields.Char(compute="_compute_display_name", store=True)
    day_label = fields.Char(compute="_compute_day_label", store=True)

    @api.depends("start_datetime", "end_datetime")
    def _compute_display_name(self):
        for rec in self:
            if not rec.start_datetime or not rec.end_datetime:
                rec.display_name = ""
                continue
            start = fields.Datetime.context_timestamp(rec, rec.start_datetime)
            end = fields.Datetime.context_timestamp(rec, rec.end_datetime)
            rec.display_name = f"{start.strftime('%a %d/%m %H:%M')} – {end.strftime('%H:%M')}"

    @api.depends("start_datetime")
    def _compute_day_label(self):
        days_es = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        for rec in self:
            if not rec.start_datetime:
                rec.day_label = ""
                continue
            start = fields.Datetime.context_timestamp(rec, rec.start_datetime)
            rec.day_label = f"{days_es[start.weekday()]} {start.strftime('%d/%m/%Y')}"

    def action_select_slot(self):
        """Create the appointment from this slot and close the wizard."""
        self.ensure_one()
        w = self.wizard_id
        if not w:
            raise UserError(_("El asistente ya no existe."))

        vals = {
            "patient_id": w.patient_id.id,
            "practitioner_id": w.practitioner_id.id,
            "practice_id": w.practice_id.id if w.practice_id else False,
            "coverage_id": w.coverage_id.id if w.coverage_id else False,
            "billing_route_id": (w.billing_route_id or w.location_id.billing_route_id).id,
            "start_datetime": self.start_datetime,
            "duration_minutes": w.duration_minutes,
            "is_overbooking": w.is_overbooking,
            "appointment_reason": w.appointment_reason or False,
            "state": "pending",
            "location_id": w.location_id.id,
        }
        appointment = self.env["clinic.appointment"].create(vals)

        # Open the new appointment so the user can review/confirm it
        return {
            "type": "ir.actions.act_window",
            "name": "Turno creado",
            "res_model": "clinic.appointment",
            "res_id": appointment.id,
            "view_mode": "form",
            "target": "current",
        }
