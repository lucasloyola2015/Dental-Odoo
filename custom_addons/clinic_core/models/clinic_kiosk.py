import secrets

from odoo import _, api, fields, models


class ClinicKiosk(models.Model):
    """Kiosk PC at a clinic entrance — patients enter their DNI to self-check-in.

    Each kiosk has a unique token that goes in the URL: /kiosk/<token>. The
    token is also the only auth: a kiosk with a leaked token can be used by
    anyone with network access, so consider rotating tokens periodically.
    """

    _name = "clinic.kiosk"
    _description = "Kiosko de check-in"
    _order = "name"

    name = fields.Char(
        string="Nombre",
        required=True,
        help="Nombre interno del kiosko. Ej: 'Recepción Roldán'.",
    )
    token = fields.Char(
        string="Token URL",
        required=True,
        readonly=True,
        index=True,
        copy=False,
        default=lambda self: secrets.token_urlsafe(24),
        help="Token único en la URL del kiosko. Inmutable. Rotalo con el botón de la cabecera.",
    )
    location_id = fields.Many2one(
        comodel_name="clinic.location",
        string="Sede",
        required=True,
        ondelete="restrict",
        help="Sólo se aceptan check-ins para turnos en esta sede.",
    )
    active = fields.Boolean(default=True)
    last_check_in_at = fields.Datetime(
        string="Último check-in",
        readonly=True,
    )
    url = fields.Char(
        string="URL del kiosko",
        compute="_compute_url",
        help="Abrí esta URL en la PC de la entrada (modo kiosk del browser).",
    )

    _token_unique = models.Constraint(
        "unique (token)",
        "El token de un kiosko debe ser único.",
    )

    @api.depends("token")
    def _compute_url(self):
        base = self.env["ir.config_parameter"].sudo().get_param(
            "web.base.url", "http://localhost:8069"
        )
        for rec in self:
            rec.url = f"{base}/kiosk/{rec.token}" if rec.token else ""

    def action_rotate_token(self):
        """Generate a fresh token. Old URL stops working immediately."""
        for rec in self:
            rec.token = secrets.token_urlsafe(24)
        return True
