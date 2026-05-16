from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicPractitionerRole(models.Model):
    """Rol de un profesional EN UNA SEDE FÍSICA.

    FHIR PractitionerRole. Un mismo employee puede tener N roles, uno por sede,
    con horarios laborales (`resource_calendar_id`), OS aceptadas y vías de
    facturación distintos en cada una.

    Refactor 2026-05-16: company_id reemplazado por location_id (decisión P).
    company_id queda como related stored desde location para compat con multi-company
    nativo de Odoo y filtros de seguridad.
    """

    _name = "clinic.practitioner.role"
    _description = "Rol del profesional en una sede (FHIR PractitionerRole)"
    _inherit = ["mail.thread"]
    _order = "employee_id, location_id"
    _rec_name = "display_name"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Profesional",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
        domain="[('is_clinic_practitioner', '=', True)]",
    )
    location_id = fields.Many2one(
        comodel_name="clinic.location",
        string="Sucursal",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        help="Sede física donde el profesional trabaja con este horario y configuración.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        related="location_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )
    resource_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Horario laboral",
        help=(
            "Horario laboral del profesional EN ESTA SEDE. "
            "Reemplaza al resource_calendar_id del empleado para el cálculo de disponibilidad "
            "cuando el profesional trabaja en varias sedes."
        ),
    )
    assigned_route_id = fields.Many2one(
        comodel_name="clinic.billing.route",
        string="Modalidad",
        required=True,
        tracking=True,
        ondelete="restrict",
        domain="[('id', 'in', allowed_route_ids)]",
        default=lambda self: self._default_assigned_route_id(),
        help=(
            "Vía con la que el profesional atiende en esta sede. "
            "Solo se permite la asociación de la sede (ej. AOSS, ASOR) o 'PARTICULAR' "
            "para atender solo particular."
        ),
    )
    allowed_route_ids = fields.Many2many(
        comodel_name="clinic.billing.route",
        compute="_compute_allowed_route_ids",
        string="Vías permitidas",
        help="Computed: la vía de la sede + el route PARTICULAR. Limita el dropdown de 'Modalidad'.",
    )
    routing_mode = fields.Selection(
        selection=[
            ("association", "Asociación heredada"),
            ("particular", "Solo Particular"),
        ],
        string="Modo de atención",
        compute="_compute_routing_mode",
        store=True,
        help="Computed desde assigned_route_id. Sirve para validations downstream.",
    )
    available_insurance_ids = fields.Many2many(
        comodel_name="clinic.health.insurance",
        relation="clinic_practitioner_role_available_insurance_rel",
        column1="role_id",
        column2="insurance_id",
        string="OS de la asociación",
        compute="_compute_effective_routing",
        store=True,
        help="OS vigentes en la vía de la sede. Limita las opciones del campo 'OS que NO acepta'.",
    )
    excluded_insurance_ids = fields.Many2many(
        comodel_name="clinic.health.insurance",
        relation="clinic_practitioner_role_excluded_insurance_rel",
        column1="role_id",
        column2="insurance_id",
        string="OS que NO acepta",
        domain="[('id', 'in', available_insurance_ids)]",
        help=(
            "Obras sociales que el profesional NO atiende, aunque estén vigentes en la "
            "asociación de la sede. Solo se pueden seleccionar OS de la asociación heredada. "
            "Por defecto vacío = acepta todas las OS de la vía."
        ),
    )
    effective_billing_route_id = fields.Many2one(
        comodel_name="clinic.billing.route",
        string="Vía efectiva",
        compute="_compute_effective_routing",
        store=True,
        help="Vía de facturación que aplica al profe en esta sede (vacío si solo atiende particular).",
    )
    effective_insurance_ids = fields.Many2many(
        comodel_name="clinic.health.insurance",
        relation="clinic_practitioner_role_effective_insurance_rel",
        column1="role_id",
        column2="insurance_id",
        string="OS efectivas",
        compute="_compute_effective_routing",
        store=True,
        help="OS vigentes en la asociación de la sede menos las excluidas explícitamente.",
    )
    particular_percentage = fields.Float(
        string="% sobre Colegio (particular)",
        default=100.0,
        tracking=True,
        help=(
            "Porcentaje del precio del Colegio (tarifa PARTICULAR) que el profesional cobra "
            "cuando atiende particular en esta sede. 100 = igual al Colegio; 80 = descuento; 120 = recargo."
        ),
    )
    gcal_calendar_id = fields.Char(
        string="Google Calendar ID",
        help="ID del calendario en Google Calendar para sync (V2).",
    )
    calendar_color = fields.Char(
        string="Color (hex)",
        help="Color para mostrar los turnos del profesional en la vista calendar. Ej: #1f77b4.",
        default="#1f77b4",
    )
    valid_from = fields.Date(string="Vigente desde", default=fields.Date.context_today, tracking=True)
    valid_to = fields.Date(string="Vigente hasta", tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    notes = fields.Text(string="Notas")
    display_name = fields.Char(compute="_compute_display_name", store=True)

    _employee_location_unique = models.Constraint(
        "unique (employee_id, location_id)",
        "El profesional ya tiene un rol asignado en esta sede. Edítalo o creá una vigencia distinta.",
    )

    @api.depends("employee_id.name", "location_id.display_name")
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or "?"
            loc = rec.location_id.display_name or "?"
            rec.display_name = f"{emp} @ {loc}"

    @api.model
    def _get_particular_route(self):
        """Return the global 'PARTICULAR' billing_route used to mark particular-only roles."""
        return self.env.ref("clinic_core.billing_route_particular", raise_if_not_found=False)

    @api.model
    def _default_assigned_route_id(self):
        """Default assigned_route on create: the location's billing_route (if known via context)."""
        loc_id = self.env.context.get("default_location_id")
        if loc_id:
            loc = self.env["clinic.location"].browse(loc_id)
            if loc.billing_route_id:
                return loc.billing_route_id.id
        return False

    @api.depends("location_id.billing_route_id")
    def _compute_allowed_route_ids(self):
        """Allowed routes for assigned_route_id: location's route + PARTICULAR."""
        particular = self._get_particular_route()
        for rec in self:
            allowed = self.env["clinic.billing.route"]
            if rec.location_id.billing_route_id:
                allowed |= rec.location_id.billing_route_id
            if particular:
                allowed |= particular
            rec.allowed_route_ids = allowed

    @api.depends("assigned_route_id")
    def _compute_routing_mode(self):
        particular = self._get_particular_route()
        particular_id = particular.id if particular else False
        for rec in self:
            if rec.assigned_route_id and rec.assigned_route_id.id == particular_id:
                rec.routing_mode = "particular"
            elif rec.assigned_route_id:
                rec.routing_mode = "association"
            else:
                # Unset assigned_route_id (transitional during onchange) — treat as particular
                rec.routing_mode = "particular"

    @api.onchange("location_id")
    def _onchange_location_default_route(self):
        """When the location changes in the form, default assigned_route to its billing_route."""
        if self.location_id and self.location_id.billing_route_id:
            self.assigned_route_id = self.location_id.billing_route_id

    @api.depends(
        "assigned_route_id",
        "routing_mode",
        "location_id.billing_route_id",
        "excluded_insurance_ids",
    )
    def _compute_effective_routing(self):
        """Derive available + effective billing_route and insurance list from the role config.

        - `available_insurance_ids`: OS vigentes en la vía de la sede (sin filtrar excluidas).
          Sirve para limitar el dropdown de exclusiones a OS reales de la asociación.
        - `effective_billing_route_id`: vía de la sede si routing_mode='association', else False.
        - `effective_insurance_ids`: available menos excluidas, si routing_mode='association', else vacío.
        """
        today = fields.Date.context_today(self)
        InsuranceRoute = self.env["clinic.insurance.route"]
        for rec in self:
            if rec.routing_mode != "association" or not rec.location_id.billing_route_id:
                rec.effective_billing_route_id = False
                rec.available_insurance_ids = [(5, 0, 0)]
                rec.effective_insurance_ids = [(5, 0, 0)]
                continue
            route = rec.location_id.billing_route_id
            rec.effective_billing_route_id = route
            insurance_routes = InsuranceRoute.search([
                ("billing_route_id", "=", route.id),
                ("accepts", "=", True),
                ("active", "=", True),
                ("valid_from", "<=", today),
                "|", ("valid_to", "=", False), ("valid_to", ">=", today),
            ])
            available = insurance_routes.mapped("health_insurance_id")
            rec.available_insurance_ids = [(6, 0, available.ids)]
            effective = available - rec.excluded_insurance_ids
            rec.effective_insurance_ids = [(6, 0, effective.ids)]

    @api.constrains("valid_to", "valid_from")
    def _check_dates(self):
        for rec in self:
            if rec.valid_to and rec.valid_from and rec.valid_to < rec.valid_from:
                raise ValidationError(_("Vigente hasta no puede ser anterior a Vigente desde."))

    @api.constrains("particular_percentage")
    def _check_particular_percentage(self):
        for rec in self:
            if rec.particular_percentage < 0:
                raise ValidationError(_("El %% sobre Colegio no puede ser negativo."))

    @api.constrains("excluded_insurance_ids", "available_insurance_ids")
    def _check_excluded_subset_of_available(self):
        """Excluded OS must always be a subset of available OS.

        Applies in both modes:
        - association: invalid means OS not in the location's route.
        - particular: available is empty → any excluded OS is invalid.

        The UI already blocks this via the dropdown domain; this constraint guarantees
        integrity for programmatic writes too.
        """
        for rec in self:
            if not rec.excluded_insurance_ids:
                continue
            invalid = rec.excluded_insurance_ids - rec.available_insurance_ids
            if invalid:
                if rec.routing_mode == "particular":
                    raise ValidationError(_(
                        "En modalidad PARTICULAR no se pueden cargar OS excluidas "
                        "(el profesional no atiende ninguna OS en esta sede)."
                    ))
                raise ValidationError(_(
                    "Las siguientes OS no pertenecen a la asociación %(route)s de la sede %(loc)s "
                    "y por lo tanto no se pueden excluir: %(os)s"
                ) % {
                    "route": rec.location_id.billing_route_id.code or "?",
                    "loc": rec.location_id.display_name or "?",
                    "os": ", ".join(invalid.mapped("name")),
                })

    # -------------------------------------------------------------------------
    # Auto-clean excluded_insurance_ids when switching to particular-only mode
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        particular = self._get_particular_route()
        particular_id = particular.id if particular else False
        for vals in vals_list:
            if particular_id and vals.get("assigned_route_id") == particular_id:
                vals["excluded_insurance_ids"] = [(5, 0, 0)]
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if "assigned_route_id" in vals:
            particular = self._get_particular_route()
            particular_id = particular.id if particular else False
            if vals["assigned_route_id"] == particular_id:
                for rec in self:
                    if rec.excluded_insurance_ids:
                        rec.excluded_insurance_ids = [(5, 0, 0)]
        return res

    @api.onchange("assigned_route_id")
    def _onchange_assigned_route_clear_excluded(self):
        """In the form, immediately wipe the exclusion list when switching to PARTICULAR."""
        particular = self._get_particular_route()
        if particular and self.assigned_route_id == particular:
            self.excluded_insurance_ids = [(5, 0, 0)]

    @api.constrains("resource_calendar_id", "location_id")
    def _check_calendar_company(self):
        """The resource.calendar must belong to the same company as the location (or be shared)."""
        for rec in self:
            if not rec.resource_calendar_id or not rec.location_id:
                continue
            cal_company = rec.resource_calendar_id.company_id
            loc_company = rec.location_id.company_id
            if cal_company and cal_company != loc_company:
                raise ValidationError(_(
                    "El horario %(cal)s pertenece a otra compañía que la sede %(loc)s."
                ) % {"cal": rec.resource_calendar_id.name, "loc": rec.location_id.display_name})

    # -------------------------------------------------------------------------
    # Schedule editor — opens the resource.calendar of this role in a custom modal
    # -------------------------------------------------------------------------
    def action_open_schedule(self):
        """Open the schedule editor modal (custom form of resource.calendar).

        If the role has no resource_calendar_id yet, create one on-the-fly named
        "Horario {employee} @ {location.code}" so the user can start filling it.
        """
        self.ensure_one()
        if not self.resource_calendar_id:
            self.resource_calendar_id = self.env["resource.calendar"].create({
                "name": self._build_calendar_name(),
                "tz": self.env.user.tz or "America/Argentina/Buenos_Aires",
                "company_id": self.company_id.id,
                "attendance_ids": [],
            })
        return {
            "type": "ir.actions.act_window",
            "name": _("Horarios — %s") % self.display_name,
            "res_model": "resource.calendar",
            "res_id": self.resource_calendar_id.id,
            "view_mode": "form",
            "view_id": self.env.ref("clinic_core.view_clinic_schedule_calendar_form").id,
            "target": "new",
            "context": {"clinic_schedule_modal": True},
        }

    def _build_calendar_name(self):
        self.ensure_one()
        emp = self.employee_id.name or "?"
        loc = self.location_id.code or self.location_id.display_name or "?"
        return f"Horario {emp} @ {loc}"
