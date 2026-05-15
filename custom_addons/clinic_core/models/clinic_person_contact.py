from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicPersonContact(models.Model):
    _name = "clinic.person.contact"
    _description = "Vínculo entre persona y canal de contacto"
    _order = "is_primary desc, role, id"
    _rec_name = "display_name"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Persona",
        required=True,
        ondelete="cascade",
        index=True,
    )
    contact_id = fields.Many2one(
        comodel_name="clinic.contact",
        string="Canal",
        required=True,
        ondelete="restrict",
        index=True,
    )
    role = fields.Selection(
        selection=[
            ("own", "Propio"),
            ("manager", "Gestor de"),
            ("other", "Otro"),
        ],
        string="Rol",
        required=True,
        default="own",
        help=(
            "Propio: el canal pertenece a la persona. "
            "Gestor de: la persona gestiona el canal por otro (típicamente padre por hijo)."
        ),
    )
    is_primary = fields.Boolean(
        string="Principal",
        default=False,
        help="Marca este canal como el preferido para ese tipo (uno por persona y tipo).",
    )
    contact_type = fields.Selection(
        related="contact_id.type",
        string="Tipo canal",
        store=True,
    )
    contact_value_display = fields.Char(
        related="contact_id.value_display",
        string="Valor del canal",
    )
    start_date = fields.Date(string="Vigente desde", default=fields.Date.context_today)
    end_date = fields.Date(string="Vigente hasta")
    notes = fields.Text(string="Notas")
    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("partner_id.display_name", "contact_id.display_name", "role")
    def _compute_display_name(self):
        role_labels = dict(self._fields["role"].selection)
        for rec in self:
            rec.display_name = (
                f"{rec.partner_id.display_name or '?'} ← {role_labels.get(rec.role, '')} → "
                f"{rec.contact_id.display_name or '?'}"
            )

    @api.constrains("is_primary", "partner_id", "contact_type")
    def _check_single_primary_per_type(self):
        for rec in self.filtered("is_primary"):
            duplicates = self.search_count([
                ("id", "!=", rec.id),
                ("partner_id", "=", rec.partner_id.id),
                ("contact_type", "=", rec.contact_type),
                ("is_primary", "=", True),
                ("end_date", "=", False),
            ])
            if duplicates:
                raise ValidationError(
                    _("Ya hay otro canal principal del mismo tipo para %s.") % rec.partner_id.display_name
                )

    @api.constrains("end_date", "start_date")
    def _check_dates(self):
        for rec in self:
            if rec.end_date and rec.start_date and rec.end_date < rec.start_date:
                raise ValidationError(_("La fecha de baja no puede ser anterior a la de alta."))
