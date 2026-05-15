import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_clinic_person = fields.Boolean(
        string="Persona Clínica",
        default=False,
        index=True,
        help="Marca este contacto como una persona física manejada por el módulo de clínica.",
    )
    birthdate = fields.Date(
        string="Fecha de Nacimiento",
        tracking=True,
    )
    gender = fields.Selection(
        selection=[
            ("male", "Masculino"),
            ("female", "Femenino"),
            ("non_binary", "No binario"),
            ("prefer_not_to_say", "Prefiere no decir"),
            ("other", "Otro"),
        ],
        string="Género",
        tracking=True,
    )
    clinic_observations = fields.Text(
        string="Observaciones",
        help="Texto libre con información relevante para la atención. Lo lee el equipo clínico.",
    )
    age = fields.Integer(
        string="Edad",
        compute="_compute_age",
        help="Calculada a partir de la fecha de nacimiento. No se persiste — se recalcula en cada lectura.",
    )

    @api.depends("birthdate")
    def _compute_age(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.birthdate:
                rec.age = 0
                continue
            age = today.year - rec.birthdate.year
            if (today.month, today.day) < (rec.birthdate.month, rec.birthdate.day):
                age -= 1
            rec.age = age

    # --- Patients (relations via _inherits) ---
    clinic_patient_ids = fields.One2many(
        comodel_name="clinic.patient",
        inverse_name="partner_id",
        string="Pacientes",
    )
    clinic_patient_count = fields.Integer(compute="_compute_clinic_patient_count")
    is_clinic_patient = fields.Boolean(
        string="Es paciente",
        compute="_compute_is_clinic_patient",
        store=True,
        help="True si esta persona tiene al menos un registro como paciente activo.",
    )

    @api.depends("clinic_patient_ids", "clinic_patient_ids.active")
    def _compute_is_clinic_patient(self):
        for rec in self:
            rec.is_clinic_patient = bool(rec.clinic_patient_ids.filtered("active"))

    # --- Human links (bidirectional: each row has a mirror) ---
    clinic_link_as_a_ids = fields.One2many(
        comodel_name="clinic.person.link",
        inverse_name="partner_a_id",
        string="Vínculos (como A)",
    )
    clinic_link_as_b_ids = fields.One2many(
        comodel_name="clinic.person.link",
        inverse_name="partner_b_id",
        string="Vínculos (como B)",
    )

    @api.depends("clinic_patient_ids")
    def _compute_clinic_patient_count(self):
        for rec in self:
            rec.clinic_patient_count = len(rec.clinic_patient_ids)

    # -------------------------------------------------------------------------
    # DNI validation for clinic persons (Argentina: 7 or 8 digits, no CUIT)
    # -------------------------------------------------------------------------
    @api.constrains("vat", "is_clinic_person")
    def _check_dni_format(self):
        for rec in self:
            if not rec.is_clinic_person or not rec.vat:
                continue
            cleaned = re.sub(r"[\s\.\-]", "", rec.vat)
            if not re.fullmatch(r"\d{7,8}", cleaned):
                raise ValidationError(_(
                    "El DNI debe contener entre 7 y 8 dígitos numéricos. "
                    "Recibí: '%s'. Ejemplo válido: 30234567."
                ) % rec.vat)

    @api.onchange("vat")
    def _onchange_vat_normalize_dni(self):
        """Strip dots/dashes/spaces from DNI when entered on clinic persons."""
        if self.is_clinic_person and self.vat:
            self.vat = re.sub(r"[\s\.\-]", "", self.vat)

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        """Allow searching res.partner by DNI when the term looks like one.

        Lets the user type a DNI in any Many2one(res.partner) and get the match
        without having to remember the name. Falls back to standard name_search.
        """
        if name:
            cleaned = re.sub(r"[\s\.\-]", "", name)
            if re.fullmatch(r"\d{7,8}", cleaned):
                from odoo.fields import Domain
                base = Domain("vat", "=", cleaned)
                full = base & Domain(domain) if domain else base
                results = self.search(full, limit=limit)
                if results:
                    return [(p.id, p.display_name) for p in results]
        return super().name_search(name=name, domain=domain, operator=operator, limit=limit)

    def action_view_clinic_patients(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("clinic_core.action_clinic_patient")
        if self.clinic_patient_count == 1:
            action.update({
                "view_mode": "form",
                "res_id": self.clinic_patient_ids[:1].id,
                "views": [(False, "form")],
            })
        else:
            action.update({
                "domain": [("partner_id", "=", self.id)],
                "context": {"default_partner_id": self.id},
            })
        return action
