from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicLocation(models.Model):
    """Sucursal física de la clínica.

    Una `res.company` (entidad legal) puede tener N `clinic.location` (sedes físicas).
    Cada sede tiene su propia asociación regional (billing_route_id) que nuclea
    sus tarifas, su dirección y su info de contacto.

    Modelos que dependen de location:
    - clinic.practitioner.role  → horario laboral del profe POR sede
    - clinic.practitioner.practice → precios particulares POR sede
    - clinic.appointment         → en qué sede ocurre el turno

    Ver decisión P en docs/decisiones-modelo.md.
    """

    _name = "clinic.location"
    _description = "Sucursal física de la clínica (FHIR Location)"
    _inherit = ["mail.thread"]
    _order = "sequence, name"
    _rec_name = "display_name"

    name = fields.Char(
        string="Nombre",
        required=True,
        tracking=True,
        help="Nombre descriptivo de la sucursal. Ej: 'Roldán Centro', 'Funes'.",
    )
    code = fields.Char(
        string="Código",
        required=True,
        tracking=True,
        help="Código corto para identificar la sucursal en listas. Ej: 'ROL', 'FUN'.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help="Empresa legal a la que pertenece esta sucursal.",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contacto",
        ondelete="restrict",
        help=(
            "Partner que guarda la dirección, teléfono y email de la sede. "
            "Se crea automáticamente al guardar si no se indica uno."
        ),
    )
    billing_route_id = fields.Many2one(
        comodel_name="clinic.billing.route",
        string="Asociación / vía default",
        required=True,
        tracking=True,
        ondelete="restrict",
        help=(
            "Asociación regional que nuclea las tarifas de esta sucursal. "
            "Ej: AOSS, ASOR. Define los precios que aplican en esta sede."
        ),
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, tracking=True)
    notes = fields.Text(string="Notas operativas")

    # ---- Reverse relations for smart buttons ----
    practitioner_role_ids = fields.One2many(
        comodel_name="clinic.practitioner.role",
        inverse_name="location_id",
        string="Roles en esta sede",
    )
    appointment_ids = fields.One2many(
        comodel_name="clinic.appointment",
        inverse_name="location_id",
        string="Turnos en esta sede",
    )
    practitioner_count = fields.Integer(
        string="Profesionales",
        compute="_compute_smart_counts",
        help="Cantidad de profesionales con rol activo en esta sede.",
    )
    appointment_count = fields.Integer(
        string="Turnos",
        compute="_compute_smart_counts",
        help="Cantidad total de turnos cargados en esta sede.",
    )

    # ---- Related fields from partner_id (for the form ergonomics) ----
    street = fields.Char(related="partner_id.street", readonly=False)
    street2 = fields.Char(related="partner_id.street2", readonly=False)
    city = fields.Char(related="partner_id.city", readonly=False)
    state_id = fields.Many2one(related="partner_id.state_id", readonly=False)
    zip = fields.Char(related="partner_id.zip", readonly=False)
    country_id = fields.Many2one(related="partner_id.country_id", readonly=False)
    phone = fields.Char(related="partner_id.phone", readonly=False)
    email = fields.Char(related="partner_id.email", readonly=False)

    display_name = fields.Char(compute="_compute_display_name", store=True)

    _code_company_unique = models.Constraint(
        "unique (code, company_id)",
        "Ya existe una sucursal con ese código en la compañía.",
    )

    @api.depends("name", "code")
    def _compute_display_name(self):
        for rec in self:
            if rec.code and rec.name:
                rec.display_name = f"[{rec.code}] {rec.name}"
            else:
                rec.display_name = rec.name or rec.code or "Sucursal"

    @api.constrains("billing_route_id", "company_id")
    def _check_billing_route_company(self):
        """The billing route must be either shared (no company) or belong to this company."""
        for rec in self:
            if not rec.billing_route_id or not rec.company_id:
                continue
            r_company = rec.billing_route_id.company_id
            if r_company and r_company != rec.company_id:
                raise ValidationError(_(
                    "La vía de facturación %(route)s pertenece a otra compañía."
                ) % {"route": rec.billing_route_id.name})

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-create a res.partner for the location if none provided."""
        Partner = self.env["res.partner"]
        for vals in vals_list:
            if not vals.get("partner_id"):
                partner = Partner.create({
                    "name": vals.get("name") or "Sucursal",
                    "company_id": vals.get("company_id"),
                })
                vals["partner_id"] = partner.id
        return super().create(vals_list)

    def write(self, vals):
        """Keep partner.name in sync with location.name."""
        res = super().write(vals)
        if "name" in vals:
            for rec in self:
                if rec.partner_id and rec.partner_id.name != rec.name:
                    rec.partner_id.name = rec.name
        return res

    # -------------------------------------------------------------------------
    # Smart buttons
    # -------------------------------------------------------------------------
    @api.depends("practitioner_role_ids", "appointment_ids")
    def _compute_smart_counts(self):
        Role = self.env["clinic.practitioner.role"]
        Appt = self.env["clinic.appointment"]
        for rec in self:
            rec.practitioner_count = Role.search_count([
                ("location_id", "=", rec.id),
                ("active", "=", True),
            ])
            rec.appointment_count = Appt.search_count([
                ("location_id", "=", rec.id),
            ])

    def action_view_practitioners(self):
        """Open the list of practitioners working at this sede (via their roles)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Profesionales — %s") % self.display_name,
            "res_model": "clinic.practitioner.role",
            "view_mode": "list,form",
            "domain": [("location_id", "=", self.id)],
            "context": {"default_location_id": self.id},
        }

    def action_view_appointments(self):
        """Open the appointments scheduled at this sede, defaulting to calendar view."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("clinic_core.action_clinic_appointment")
        action.update({
            "name": _("Agenda — %s") % self.display_name,
            "domain": [("location_id", "=", self.id)],
            "context": {"default_location_id": self.id, "search_default_filter_upcoming": 0},
            "view_mode": "calendar,list,form",
        })
        return action
