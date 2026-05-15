import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicContact(models.Model):
    _name = "clinic.contact"
    _description = "Canal de contacto (WhatsApp / email / teléfono)"
    _order = "type, value"
    _rec_name = "display_name"

    type = fields.Selection(
        selection=[
            ("whatsapp", "WhatsApp"),
            ("email", "Email"),
            ("phone_mobile", "Teléfono móvil"),
            ("phone_fixed", "Teléfono fijo"),
            ("other", "Otro"),
        ],
        string="Tipo",
        required=True,
        default="whatsapp",
    )
    value = fields.Char(
        string="Valor",
        required=True,
        help="Número en formato E.164 (+5493411234567) o email lowercase.",
    )
    value_display = fields.Char(
        string="Display",
        compute="_compute_value_display",
        store=True,
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)
    verified = fields.Boolean(string="Verificado")
    verified_at = fields.Datetime(string="Verificado en")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    start_date = fields.Date(string="Vigente desde", default=fields.Date.context_today)
    end_date = fields.Date(string="Vigente hasta")
    notes = fields.Text(string="Notas")
    person_contact_ids = fields.One2many(
        comodel_name="clinic.person.contact",
        inverse_name="contact_id",
        string="Personas vinculadas",
    )

    _value_unique_per_company = models.Constraint(
        "unique (type, value, company_id)",
        "Ya existe un canal con ese tipo y valor en la compañía.",
    )

    @api.depends("type", "value")
    def _compute_value_display(self):
        for rec in self:
            if not rec.value:
                rec.value_display = False
            elif rec.type in ("whatsapp", "phone_mobile", "phone_fixed"):
                rec.value_display = rec._format_phone_for_display(rec.value)
            else:
                rec.value_display = rec.value

    @api.depends("type", "value_display")
    def _compute_display_name(self):
        type_labels = dict(self._fields["type"].selection)
        for rec in self:
            rec.display_name = f"{type_labels.get(rec.type, '')}: {rec.value_display or rec.value or '?'}"

    @staticmethod
    def _format_phone_for_display(value):
        digits = re.sub(r"\D", "", value or "")
        if len(digits) >= 10:
            return f"+{digits[:-10]} {digits[-10:-7]} {digits[-7:-4]}-{digits[-4:]}".strip()
        return value

    @api.constrains("type", "value")
    def _check_value_format(self):
        for rec in self:
            if not rec.value:
                continue
            if rec.type == "email":
                if "@" not in rec.value or " " in rec.value:
                    raise ValidationError(_("El email '%s' no parece válido.") % rec.value)
            elif rec.type in ("whatsapp", "phone_mobile", "phone_fixed"):
                if not rec.value.startswith("+") or not re.fullmatch(r"\+\d{8,15}", rec.value):
                    raise ValidationError(
                        _("El número '%s' debe estar en formato E.164 (ej. +5493411234567).") % rec.value
                    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["value"] = self._normalize_value(vals.get("type"), vals.get("value"))
        return super().create(vals_list)

    def write(self, vals):
        if "value" in vals or "type" in vals:
            for rec in self:
                new_type = vals.get("type", rec.type)
                new_value = vals.get("value", rec.value)
                vals["value"] = self._normalize_value(new_type, new_value)
                break
        return super().write(vals)

    @staticmethod
    def _normalize_value(type_, value):
        if not value:
            return value
        if type_ == "email":
            return value.strip().lower()
        if type_ in ("whatsapp", "phone_mobile", "phone_fixed"):
            stripped = re.sub(r"[\s\-\(\)]", "", value)
            return stripped
        return value
