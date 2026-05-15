from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ClinicAppointment(models.Model):
    _name = "clinic.appointment"
    _description = "Turno clínico"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_datetime desc, id desc"
    _rec_name = "display_name"
    _check_company_auto = True

    # -------------------------------------------------------------------------
    # Identification
    # -------------------------------------------------------------------------
    patient_id = fields.Many2one(
        comodel_name="clinic.patient",
        string="Paciente",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        check_company=True,
    )
    practitioner_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Profesional",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        domain="[('is_clinic_practitioner', '=', True)]",
    )
    practice_id = fields.Many2one(
        comodel_name="clinic.practice",
        string="Práctica",
        ondelete="restrict",
        tracking=True,
        help="Práctica FACO a realizar. Vacío = consulta general / no definido todavía.",
    )
    coverage_id = fields.Many2one(
        comodel_name="clinic.patient.coverage",
        string="Cobertura",
        ondelete="restrict",
        tracking=True,
        domain="[('patient_id', '=', patient_id)]",
        help="Cobertura del paciente que aplica a este turno. Vacío = particular.",
    )
    billing_route_id = fields.Many2one(
        comodel_name="clinic.billing.route",
        string="Vía de facturación",
        ondelete="restrict",
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )

    # -------------------------------------------------------------------------
    # Schedule
    # -------------------------------------------------------------------------
    start_datetime = fields.Datetime(
        string="Inicio",
        required=True,
        index=True,
        tracking=True,
    )
    duration_minutes = fields.Integer(
        string="Duración (min)",
        required=True,
        default=30,
        tracking=True,
    )
    end_datetime = fields.Datetime(
        string="Fin",
        compute="_compute_end_datetime",
        store=True,
        index=True,
    )
    is_overbooking = fields.Boolean(
        string="Sobreturno",
        default=False,
        tracking=True,
        help="Marca este turno como excepcional fuera de la grilla habitual. Bypassa validación de horario laboral.",
    )

    # -------------------------------------------------------------------------
    # State machine (FHIR-style)
    # -------------------------------------------------------------------------
    state = fields.Selection(
        selection=[
            ("proposed", "Propuesto"),       # Bot lo sugirió, paciente no confirmó (V2)
            ("pending", "Pendiente"),         # Secretaría agendó, falta confirmar
            ("booked", "Confirmado"),         # Confirmado por paciente o por secretaría
            ("checked-in", "Registrado"),     # Paciente llegó y está en recepción
            ("arrived", "En consulta"),       # Pasó al consultorio
            ("fulfilled", "Atendido"),        # Terminó OK
            ("cancelled", "Cancelado"),       # Cancelado por alguna parte
            ("noshow", "No asistió"),         # Paciente no se presentó
            ("waitlist", "En lista de espera"),  # V2
            ("entered-in-error", "Cargado por error"),  # Error / borrado lógico
        ],
        string="Estado",
        default="pending",
        required=True,
        tracking=True,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Content
    # -------------------------------------------------------------------------
    appointment_reason = fields.Text(
        string="Motivo de consulta",
        help='Lo que dijo el paciente. NO es diagnóstico.',
    )
    internal_notes = fields.Text(string="Notas internas")
    cancellation_reason = fields.Char(string="Motivo de cancelación", tracking=True)

    # -------------------------------------------------------------------------
    # Display
    # -------------------------------------------------------------------------
    display_name = fields.Char(compute="_compute_display_name", store=True)

    _duration_positive = models.Constraint(
        "check (duration_minutes > 0)",
        "La duración del turno debe ser mayor a cero.",
    )

    # -------------------------------------------------------------------------
    # Computes
    # -------------------------------------------------------------------------
    @api.depends("start_datetime", "duration_minutes")
    def _compute_end_datetime(self):
        for rec in self:
            if rec.start_datetime and rec.duration_minutes:
                rec.end_datetime = rec.start_datetime + timedelta(minutes=rec.duration_minutes)
            else:
                rec.end_datetime = False

    @api.depends("patient_id.name", "practitioner_id.name", "start_datetime", "state")
    def _compute_display_name(self):
        for rec in self:
            patient = rec.patient_id.name or "?"
            prac = rec.practitioner_id.name or "?"
            when = fields.Datetime.context_timestamp(rec, rec.start_datetime).strftime("%d/%m %H:%M") if rec.start_datetime else "?"
            rec.display_name = f"{when} — {patient} con {prac}"

    # -------------------------------------------------------------------------
    # Onchanges
    # -------------------------------------------------------------------------
    @api.onchange("practitioner_id", "practice_id")
    def _onchange_practitioner_set_duration(self):
        """Apply the duration cascade when practitioner or practice changes."""
        if self.practitioner_id and (not self.duration_minutes or self._origin.duration_minutes == self.duration_minutes):
            self.duration_minutes = self.practitioner_id.get_default_appointment_duration(self.practice_id)

    @api.onchange("patient_id")
    def _onchange_patient_set_coverage(self):
        """Pre-seleccionar la cobertura principal del paciente."""
        if self.patient_id:
            primary = self.patient_id.coverage_ids.filtered(lambda c: c.is_primary and c.active)
            if primary:
                self.coverage_id = primary[0]

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------
    @api.constrains("start_datetime", "end_datetime", "practitioner_id", "state", "is_overbooking", "company_id")
    def _check_no_overlap(self):
        """No two non-cancelled appointments can overlap for the same practitioner+company,
        unless is_overbooking is True on at least one of them."""
        blocking_states = ("pending", "booked", "checked-in", "arrived", "fulfilled")
        for rec in self:
            if rec.is_overbooking:
                continue
            if rec.state not in blocking_states:
                continue
            if not (rec.start_datetime and rec.end_datetime):
                continue
            conflict = self.search_count([
                ("id", "!=", rec.id),
                ("practitioner_id", "=", rec.practitioner_id.id),
                ("company_id", "=", rec.company_id.id),
                ("is_overbooking", "=", False),
                ("state", "in", blocking_states),
                ("start_datetime", "<", rec.end_datetime),
                ("end_datetime", ">", rec.start_datetime),
            ])
            if conflict:
                raise ValidationError(_(
                    "El profesional %(prac)s ya tiene un turno superpuesto en ese horario. "
                    "Si querés ofrecer un sobreturno, marcá la casilla 'Sobreturno'."
                ) % {"prac": rec.practitioner_id.name})

    @api.constrains("coverage_id", "patient_id")
    def _check_coverage_belongs_to_patient(self):
        for rec in self:
            if rec.coverage_id and rec.coverage_id.patient_id != rec.patient_id:
                raise ValidationError(_("La cobertura seleccionada no pertenece al paciente del turno."))

    @api.constrains("practitioner_id", "company_id")
    def _check_practitioner_role_in_company(self):
        """The practitioner must have an active role in the appointment's company."""
        for rec in self:
            if not rec.practitioner_id or not rec.company_id:
                continue
            role = self.env["clinic.practitioner.role"].search([
                ("employee_id", "=", rec.practitioner_id.id),
                ("company_id", "=", rec.company_id.id),
                ("active", "=", True),
            ], limit=1)
            if not role:
                raise ValidationError(_(
                    "El profesional %(prac)s no tiene un rol activo en la compañía %(comp)s. "
                    "Cargá el rol en su ficha antes de agendar."
                ) % {"prac": rec.practitioner_id.name, "comp": rec.company_id.name})

    # -------------------------------------------------------------------------
    # State transition actions
    # -------------------------------------------------------------------------
    def action_confirm(self):
        self._set_state("booked", from_states=("proposed", "pending"))

    def action_check_in(self):
        self._set_state("checked-in", from_states=("booked",))

    def action_mark_arrived(self):
        self._set_state("arrived", from_states=("checked-in", "booked"))

    def action_complete(self):
        self._set_state("fulfilled", from_states=("arrived", "checked-in", "booked"))

    def action_mark_noshow(self):
        self._set_state("noshow", from_states=("booked", "checked-in", "pending"))

    def action_cancel(self, reason=None):
        cancellable = ("proposed", "pending", "booked", "checked-in", "waitlist")
        for rec in self:
            if rec.state not in cancellable:
                raise UserError(_("No se puede cancelar un turno en estado %s.") % rec.state)
        vals = {"state": "cancelled"}
        if reason:
            vals["cancellation_reason"] = reason
        self.write(vals)
        return True

    def action_reset_to_pending(self):
        for rec in self:
            if rec.state in ("fulfilled", "cancelled", "noshow"):
                raise UserError(_("No se puede revertir un turno %s a Pendiente.") % rec.state)
        self.write({"state": "pending"})

    def _set_state(self, target, from_states):
        for rec in self:
            if rec.state not in from_states:
                raise UserError(_(
                    "Transición no permitida: estado actual '%(curr)s' no puede pasar a '%(tgt)s'."
                ) % {"curr": rec.state, "tgt": target})
        self.write({"state": target})
        return True
