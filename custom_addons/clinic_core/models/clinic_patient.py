from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicPatient(models.Model):
    _name = "clinic.patient"
    _description = "Paciente"
    _inherits = {"res.partner": "partner_id"}
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _check_company_auto = True

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Persona",
        ondelete="cascade",
        required=True,
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    medical_history_number = fields.Char(
        string="N° Historia Clínica",
        tracking=True,
        copy=False,
        index=True,
        readonly=True,
        default=lambda self: _("New"),
        help="Generado automáticamente al crear el paciente. Formato: HC-YYYYNNNN.",
    )
    secretariat_notes = fields.Text(
        string="Notas de secretaría",
        help="Notas operativas (no clínicas). Lo lee el equipo.",
    )
    start_date = fields.Date(
        string="Paciente desde",
        default=fields.Date.context_today,
        readonly=True,
        copy=False,
        tracking=True,
        help="Se asigna automáticamente al crear el paciente.",
    )
    active = fields.Boolean(default=True, tracking=True)
    coverage_ids = fields.One2many(
        comodel_name="clinic.patient.coverage",
        inverse_name="patient_id",
        string="Coberturas (Obras sociales)",
    )

    # --- Contact target (own phone/email OR external via person link) ---
    use_external_contact = fields.Boolean(
        string="Contacto externo",
        default=False,
        help=(
            "Si se tilda, el paciente NO se contacta por sus propios teléfonos. "
            "Se contacta vía los vínculos del tab 'Vínculos' que tengan 'Puede ser contactado' tildado. "
            "Caso típico: menores sin teléfono propio, contactados via padre/madre/tutor."
        ),
    )
    external_contact_summary = fields.Text(
        string="Contactar via",
        compute="_compute_external_contact_summary",
    )

    @api.depends("partner_id", "use_external_contact")
    def _compute_external_contact_summary(self):
        Link = self.env["clinic.person.link"]
        for rec in self:
            if not rec.use_external_contact or not rec.partner_id:
                rec.external_contact_summary = False
                continue
            # Find links where this partner is partner_b (someone else has can_be_contacted over them)
            links = Link.search([
                ("partner_b_id", "=", rec.partner_id.id),
                ("can_be_contacted", "=", True),
            ])
            if not links:
                rec.external_contact_summary = (
                    "⚠ Sin contactos disponibles. Cargá un vínculo en el tab 'Vínculos' "
                    "con la casilla 'Puede ser contactado' tildada."
                )
                continue
            type_labels = dict(Link._fields["relationship_type"].selection)
            lines = []
            for link in links:
                other = link.partner_a_id
                phone_parts = []
                if other.phone:
                    phone_parts.append(f"📞 {other.phone}")
                if other.email:
                    phone_parts.append(f"✉ {other.email}")
                phones = " · ".join(phone_parts) if phone_parts else "(sin canales)"
                type_label = type_labels.get(link.relationship_type, link.relationship_type)
                lines.append(f"• {other.name} ({type_label}): {phones}")
            rec.external_contact_summary = "\n".join(lines)

    @api.constrains("use_external_contact", "partner_id")
    def _check_contact_target(self):
        Link = self.env["clinic.person.link"]
        for rec in self:
            if rec.use_external_contact:
                count = Link.search_count([
                    ("partner_b_id", "=", rec.partner_id.id),
                    ("can_be_contacted", "=", True),
                ])
                if not count:
                    raise ValidationError(_(
                        "El paciente está marcado como 'Contacto externo' pero no tiene ningún vínculo "
                        "con 'Puede ser contactado' tildado. Cargá uno en el tab 'Vínculos'."
                    ))
            else:
                p = rec.partner_id
                if not (p.phone or p.email):
                    raise ValidationError(_(
                        "El paciente debe tener teléfono o email propio. "
                        "Si su contacto es externo (ej. menor con padre como contacto), "
                        "marcá la casilla 'Contacto externo'."
                    ))
    appointment_ids = fields.One2many(
        comodel_name="clinic.appointment",
        inverse_name="patient_id",
        string="Turnos",
    )
    appointment_count = fields.Integer(compute="_compute_appointment_count")

    @api.depends("appointment_ids")
    def _compute_appointment_count(self):
        for rec in self:
            rec.appointment_count = len(rec.appointment_ids)

    def action_view_appointments(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("clinic_core.action_clinic_appointment")
        action.update({
            "domain": [("patient_id", "=", self.id)],
            "context": {"default_patient_id": self.id},
        })
        return action

    _hcn_unique_per_company = models.Constraint(
        "unique (medical_history_number, company_id)",
        "El N° de Historia Clínica debe ser único dentro de la compañía.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("partner_id", False)
            if vals.get("partner_id"):
                self.env["res.partner"].browse(vals["partner_id"]).is_clinic_person = True
            # Auto-generate HC number from sequence
            hcn = vals.get("medical_history_number")
            if not hcn or hcn == _("New"):
                seq = self.env["ir.sequence"].next_by_code("clinic.patient.hc")
                vals["medical_history_number"] = seq or "HC-NEW"
        records = super().create(vals_list)
        for rec in records:
            if not rec.partner_id.is_clinic_person:
                rec.partner_id.is_clinic_person = True
        return records

    def action_view_partner(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "res_id": self.partner_id.id,
            "view_mode": "form",
            "target": "current",
        }
