from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicInsuranceRoute(models.Model):
    _name = "clinic.insurance.route"
    _description = "Obra social aceptada por vía de facturación"
    _inherit = ["mail.thread"]
    _order = "health_insurance_id, billing_route_id, valid_from desc"
    _rec_name = "display_name"

    health_insurance_id = fields.Many2one(
        comodel_name="clinic.health.insurance",
        string="Obra social",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    billing_route_id = fields.Many2one(
        comodel_name="clinic.billing.route",
        string="Vía",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    accepts = fields.Boolean(string="Acepta", default=True, tracking=True)
    requires_authorization = fields.Boolean(string="Requiere autorización", tracking=True)
    observations = fields.Text(string="Observaciones")
    valid_from = fields.Date(string="Vigente desde", default=fields.Date.context_today, tracking=True)
    valid_to = fields.Date(string="Vigente hasta")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("health_insurance_id", "billing_route_id", "valid_from")
    def _compute_display_name(self):
        for rec in self:
            os_name = rec.health_insurance_id.name or "?"
            route_name = rec.billing_route_id.name or "?"
            rec.display_name = f"{os_name} via {route_name} (desde {rec.valid_from or '?'})"

    @api.constrains("valid_to", "valid_from")
    def _check_dates(self):
        for rec in self:
            if rec.valid_to and rec.valid_from and rec.valid_to < rec.valid_from:
                raise ValidationError(_("Vigente hasta no puede ser anterior a Vigente desde."))
