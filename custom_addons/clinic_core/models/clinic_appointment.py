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
    location_id = fields.Many2one(
        comodel_name="clinic.location",
        string="Sucursal",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        default=lambda self: self._default_location_id(),
        help="Sede física donde ocurre el turno. Define la vía de facturación default y filtra availability slots.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        related="location_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )

    @api.model
    def _default_location_id(self):
        """Pick the first active location of the current company."""
        return self.env["clinic.location"].search([
            ("company_id", "=", self.env.company.id),
            ("active", "=", True),
        ], limit=1).id or False

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
    # Valuation (tentative — see doc 05 §3.1)
    # -------------------------------------------------------------------------
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        store=True,
    )
    amount_paid_by_os = fields.Monetary(
        string="Paga OS ($)",
        currency_field="currency_id",
        compute="_compute_valuation",
        store=True,
        help="Lo que paga la obra social al profesional/asociación según tarifa vigente.",
    )
    bond_count_paid_by_os = fields.Integer(
        string="Bonos OS",
        compute="_compute_valuation",
        store=True,
        help="Cantidad de bonos que cubre la OS (sistemas tipo IAPOS).",
    )
    bond_value_amount = fields.Monetary(
        string="Valor bonos ($)",
        currency_field="currency_id",
        compute="_compute_valuation",
        store=True,
        help="bond_count_paid_by_os × valor unitario del bono vigente.",
    )
    copayment_amount = fields.Monetary(
        string="Copago OS ($)",
        currency_field="currency_id",
        compute="_compute_valuation",
        store=True,
        help="Lo que el paciente paga además, según la OS.",
    )
    professional_extra_override = fields.Monetary(
        string="Adicional profesional ($)",
        currency_field="currency_id",
        help="Override manual del extra que cobra el profesional. Dejá vacío para usar el cálculo automático.",
    )
    professional_extra_auto = fields.Monetary(
        string="Adicional profesional (auto)",
        currency_field="currency_id",
        compute="_compute_valuation",
        store=True,
        help="Calculado: precio particular para PARTICULAR, 0 para con cobertura.",
    )
    professional_extra_final = fields.Monetary(
        string="Adicional prof. aplicado",
        currency_field="currency_id",
        compute="_compute_valuation",
        store=True,
    )
    clinic_extra = fields.Monetary(
        string="Adicional clínica ($)",
        currency_field="currency_id",
        default=0.0,
        help="Adicional cobrado por la clínica. V1: editable, default 0. V2: configurable por clínica.",
    )
    total_for_patient = fields.Monetary(
        string="Total a cobrar al paciente ($)",
        currency_field="currency_id",
        compute="_compute_valuation",
        store=True,
    )
    valuation_note = fields.Text(
        string="Detalle del cálculo",
        compute="_compute_valuation",
        store=True,
    )
    tariff_id = fields.Many2one(
        comodel_name="clinic.tariff",
        string="Tarifa aplicada",
        compute="_compute_valuation",
        store=True,
        help="Tarifa OS-vía-práctica usada para el cálculo (la más reciente vigente).",
    )

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

    @api.depends(
        "patient_id", "practitioner_id", "practice_id", "coverage_id",
        "billing_route_id", "location_id", "start_datetime",
        "professional_extra_override", "clinic_extra",
    )
    def _compute_valuation(self):
        """Tentative valuation following doc 05 §3.1, V1-simplified.

        Particular:
            - amount_paid_by_os = 0, copayment = 0
            - professional_extra_auto = practitioner.practice.price_particular for this practice
            - total = (override or auto) + clinic_extra

        With coverage:
            - Find tariff (insurance + route + practice, vigente al start_datetime)
            - amount_paid_by_os from tariff
            - bond_count + bond_value from clinic.bond.system if tariff uses bonds
            - copayment from clinic.copayment (most specific: by practice, fallback to insurance-only)
            - professional_extra_auto = 0 (V1 — no adicional default with OS)
            - clinic_extra = field value (editable)
            - total = copayment + professional_extra_final + clinic_extra
        """
        Tariff = self.env["clinic.tariff"]
        Copay = self.env["clinic.copayment"]
        BondSys = self.env["clinic.bond.system"]
        PractPractice = self.env["clinic.practitioner.practice"]

        for rec in self:
            # Reset
            rec.amount_paid_by_os = 0.0
            rec.bond_count_paid_by_os = 0
            rec.bond_value_amount = 0.0
            rec.copayment_amount = 0.0
            rec.professional_extra_auto = 0.0
            rec.professional_extra_final = 0.0
            rec.total_for_patient = 0.0
            rec.valuation_note = ""
            rec.tariff_id = False

            if not rec.practice_id:
                rec.valuation_note = "Sin práctica definida — no se puede calcular presupuesto."
                continue

            ref_date = (rec.start_datetime or fields.Datetime.now()).date() if rec.start_datetime else fields.Date.today()
            is_particular = (not rec.coverage_id) or rec.coverage_id.health_insurance_id.is_particular

            notes = []

            # ----------------------------- Particular -----------------------------
            if is_particular:
                pp = PractPractice.search([
                    ("employee_id", "=", rec.practitioner_id.id),
                    ("practice_id", "=", rec.practice_id.id),
                    ("location_id", "=", rec.location_id.id),
                    ("can_perform", "=", True),
                ], limit=1)
                if pp and pp.price_particular:
                    rec.professional_extra_auto = pp.price_particular
                    notes.append(f"Particular. Precio del profesional: ${pp.price_particular:,.2f}")
                else:
                    notes.append("Particular. El profesional no tiene precio cargado para esta práctica.")

                rec.professional_extra_final = rec.professional_extra_override or rec.professional_extra_auto
                rec.total_for_patient = rec.professional_extra_final + (rec.clinic_extra or 0.0)
                if rec.professional_extra_override:
                    notes.append(f"Adicional profesional override: ${rec.professional_extra_override:,.2f}")
                if rec.clinic_extra:
                    notes.append(f"Adicional clínica: ${rec.clinic_extra:,.2f}")
                notes.append(f"TOTAL a cobrar: ${rec.total_for_patient:,.2f} (tentativo)")
                rec.valuation_note = "\n".join(notes)
                continue

            # --------------------------- With coverage ---------------------------
            insurance = rec.coverage_id.health_insurance_id
            route = rec.billing_route_id

            # Find tariff: most recent vigente <= ref_date
            tariff_domain = [
                ("health_insurance_id", "=", insurance.id),
                ("practice_id", "=", rec.practice_id.id),
                ("valid_from", "<=", ref_date),
                ("company_id", "in", (False, rec.company_id.id)),
            ]
            if route:
                tariff_domain.append(("billing_route_id", "=", route.id))
            tariff = Tariff.search(tariff_domain, order="valid_from desc", limit=1)
            if tariff:
                rec.tariff_id = tariff.id
                if tariff.amount_paid_by_os:
                    rec.amount_paid_by_os = tariff.amount_paid_by_os
                    notes.append(f"{insurance.code} paga al profesional: ${tariff.amount_paid_by_os:,.2f} (tarifa {tariff.valid_from})")
                elif tariff.bond_count:
                    rec.bond_count_paid_by_os = tariff.bond_count
                    bond_sys = BondSys.search([
                        ("health_insurance_id", "=", insurance.id),
                        ("valid_from", "<=", ref_date),
                        "|", ("billing_route_id", "=", False), ("billing_route_id", "=", route.id if route else 0),
                        ("active", "=", True),
                    ], order="valid_from desc", limit=1)
                    if bond_sys:
                        rec.bond_value_amount = tariff.bond_count * bond_sys.bond_value
                        notes.append(
                            f"{insurance.code} paga {tariff.bond_count} bonos × ${bond_sys.bond_value:,.2f} = ${rec.bond_value_amount:,.2f}"
                        )
                    else:
                        notes.append(f"{insurance.code} paga {tariff.bond_count} bonos (valor del bono no configurado).")
                if tariff.has_stamp and tariff.stamp_value:
                    notes.append(f"+ estampilla ${tariff.stamp_value:,.2f}")
            else:
                notes.append(f"⚠ Sin tarifa cargada para {insurance.code} / {rec.practice_id.faco_code} al {ref_date}.")

            # Find copayment: most specific (by practice) → fallback to insurance-only
            copay = Copay.search([
                ("health_insurance_id", "=", insurance.id),
                ("practice_id", "=", rec.practice_id.id),
                ("valid_from", "<=", ref_date),
                ("company_id", "in", (False, rec.company_id.id)),
            ], order="valid_from desc", limit=1)
            if not copay:
                copay = Copay.search([
                    ("health_insurance_id", "=", insurance.id),
                    ("practice_id", "=", False),
                    ("valid_from", "<=", ref_date),
                    ("company_id", "in", (False, rec.company_id.id)),
                ], order="valid_from desc", limit=1)
            if copay:
                rec.copayment_amount = copay.amount
                notes.append(f"Copago paciente: ${copay.amount:,.2f}")

            # Professional extra: 0 by default with OS, override manual
            rec.professional_extra_auto = 0.0
            rec.professional_extra_final = rec.professional_extra_override or 0.0
            if rec.professional_extra_override:
                notes.append(f"Adicional profesional (manual): ${rec.professional_extra_override:,.2f}")

            if rec.clinic_extra:
                notes.append(f"Adicional clínica: ${rec.clinic_extra:,.2f}")

            rec.total_for_patient = (rec.copayment_amount or 0.0) + (rec.professional_extra_final or 0.0) + (rec.clinic_extra or 0.0)
            notes.append(f"TOTAL a cobrar al paciente: ${rec.total_for_patient:,.2f} (tentativo, sujeto a tarifario vigente al día de la atención)")
            rec.valuation_note = "\n".join(notes)

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

    @api.onchange("location_id")
    def _onchange_location_default_route(self):
        """Default billing_route_id from the location's regional association."""
        if self.location_id and not self.billing_route_id:
            self.billing_route_id = self.location_id.billing_route_id

    @api.onchange("practitioner_id", "location_id")
    def _onchange_practitioner_route(self):
        """Adjust billing_route based on the practitioner's role in this location.

        If the role has routing_mode='particular', force billing_route to False.
        Otherwise default to the role's effective route.
        """
        if not self.practitioner_id or not self.location_id:
            return
        role = self.env["clinic.practitioner.role"].search([
            ("employee_id", "=", self.practitioner_id.id),
            ("location_id", "=", self.location_id.id),
            ("active", "=", True),
        ], limit=1)
        if not role:
            return
        if role.routing_mode == "particular":
            self.billing_route_id = False
        else:
            self.billing_route_id = role.effective_billing_route_id

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------
    @api.constrains("start_datetime", "end_datetime", "practitioner_id", "state", "is_overbooking", "location_id")
    def _check_no_overlap(self):
        """No two non-cancelled appointments can overlap for the same practitioner+location,
        unless is_overbooking is True on at least one of them.

        Note: overlap is per-location so a profesional puede tener un turno en Roldán
        9:00-10:00 y otro en Funes 9:30-10:30 (físicamente imposible pero el modelo
        no impide cross-location overlap — eso es responsabilidad del que agenda).
        """
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
                ("location_id", "=", rec.location_id.id),
                ("is_overbooking", "=", False),
                ("state", "in", blocking_states),
                ("start_datetime", "<", rec.end_datetime),
                ("end_datetime", ">", rec.start_datetime),
            ])
            if conflict:
                raise ValidationError(_(
                    "El profesional %(prac)s ya tiene un turno superpuesto en %(loc)s en ese horario. "
                    "Si querés ofrecer un sobreturno, marcá la casilla 'Sobreturno'."
                ) % {"prac": rec.practitioner_id.name, "loc": rec.location_id.display_name})

    @api.constrains("coverage_id", "patient_id")
    def _check_coverage_belongs_to_patient(self):
        for rec in self:
            if rec.coverage_id and rec.coverage_id.patient_id != rec.patient_id:
                raise ValidationError(_("La cobertura seleccionada no pertenece al paciente del turno."))

    @api.constrains("practitioner_id", "location_id")
    def _check_practitioner_role_in_location(self):
        """The practitioner must have an active role in the appointment's location."""
        for rec in self:
            if not rec.practitioner_id or not rec.location_id:
                continue
            role = self.env["clinic.practitioner.role"].search([
                ("employee_id", "=", rec.practitioner_id.id),
                ("location_id", "=", rec.location_id.id),
                ("active", "=", True),
            ], limit=1)
            if not role:
                raise ValidationError(_(
                    "El profesional %(prac)s no tiene un rol activo en la sede %(loc)s. "
                    "Cargá el rol en su ficha antes de agendar."
                ) % {"prac": rec.practitioner_id.name, "loc": rec.location_id.display_name})

    @api.constrains("practitioner_id", "location_id", "coverage_id")
    def _check_coverage_vs_role_routing(self):
        """If the practitioner role at this location is particular-only
        (routing_mode='particular'), reject appointments with coverage_id.

        Also reject coverage if its OS is in the role's excluded_insurance_ids.
        """
        for rec in self:
            if not (rec.practitioner_id and rec.location_id and rec.coverage_id):
                continue
            role = self.env["clinic.practitioner.role"].search([
                ("employee_id", "=", rec.practitioner_id.id),
                ("location_id", "=", rec.location_id.id),
                ("active", "=", True),
            ], limit=1)
            if not role:
                continue
            if role.routing_mode == "particular":
                raise ValidationError(_(
                    "El profesional %(prac)s solo atiende particular en la sede %(loc)s. "
                    "Quitá la cobertura o agendá con otro profesional / sede."
                ) % {"prac": rec.practitioner_id.name, "loc": rec.location_id.display_name})
            insurance = rec.coverage_id.health_insurance_id
            if insurance and insurance in role.excluded_insurance_ids:
                raise ValidationError(_(
                    "El profesional %(prac)s no atiende %(os)s en la sede %(loc)s "
                    "(está en su lista de OS excluidas)."
                ) % {
                    "prac": rec.practitioner_id.name,
                    "os": insurance.name,
                    "loc": rec.location_id.display_name,
                })

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
