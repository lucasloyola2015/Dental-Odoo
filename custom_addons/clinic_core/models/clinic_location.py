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
