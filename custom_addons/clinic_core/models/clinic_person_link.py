from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicPersonLink(models.Model):
    _name = "clinic.person.link"
    _description = "Vínculo humano entre dos personas"
    _order = "id"
    _rec_name = "display_name"

    partner_a_id = fields.Many2one(
        comodel_name="res.partner",
        string="Persona A",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_b_id = fields.Many2one(
        comodel_name="res.partner",
        string="Persona B",
        required=True,
        ondelete="cascade",
        index=True,
    )
    relationship_type = fields.Selection(
        selection=[
            ("parent", "Padre / Madre"),
            ("child", "Hijo / Hija"),
            ("spouse", "Cónyuge"),
            ("partner", "Pareja"),
            ("sibling", "Hermano / Hermana"),
            ("legal_guardian", "Tutor legal"),
            ("responsible", "Responsable"),
            ("grandparent", "Abuelo / Abuela"),
            ("grandchild", "Nieto / Nieta"),
            ("uncle_aunt", "Tío / Tía"),
            ("other", "Otro"),
        ],
        string="A es ... de B",
        required=True,
        help="Tipo de relación de A hacia B (ej: A es Padre de B).",
    )
    relationship_type_other = fields.Char(
        string="Especificar otro",
        help="Si el tipo de vínculo es 'Otro', indicar acá la descripción.",
    )
    is_legal_guardian = fields.Boolean(
        string="Responsable legal",
        help="A es responsable legal de B (padres de menores, tutores por sentencia).",
    )
    can_consent = fields.Boolean(
        string="Puede dar consentimiento",
        help="A puede firmar consentimientos médicos por B.",
    )
    can_be_contacted = fields.Boolean(
        string="Puede ser contactado",
        default=True,
        help="A puede recibir información sobre B vía canales del consultorio.",
    )
    start_date = fields.Date(string="Vigente desde", default=fields.Date.context_today)
    end_date = fields.Date(string="Vigente hasta")
    notes = fields.Text(string="Notas")
    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("partner_a_id.display_name", "partner_b_id.display_name", "relationship_type", "relationship_type_other")
    def _compute_display_name(self):
        type_labels = dict(self._fields["relationship_type"].selection)
        for rec in self:
            rel = rec.relationship_type_other if rec.relationship_type == "other" else type_labels.get(rec.relationship_type, "?")
            rec.display_name = f"{rec.partner_a_id.display_name or '?'} ← {rel} → {rec.partner_b_id.display_name or '?'}"

    @api.constrains("partner_a_id", "partner_b_id")
    def _check_different_partners(self):
        for rec in self:
            if rec.partner_a_id == rec.partner_b_id:
                raise ValidationError(_("Una persona no puede tener un vínculo consigo misma."))

    @api.constrains("relationship_type", "relationship_type_other")
    def _check_other_description(self):
        for rec in self:
            if rec.relationship_type == "other" and not rec.relationship_type_other:
                raise ValidationError(_("Si el tipo es 'Otro', tenés que describir el vínculo."))

    @api.constrains("end_date", "start_date")
    def _check_dates(self):
        for rec in self:
            if rec.end_date and rec.start_date and rec.end_date < rec.start_date:
                raise ValidationError(_("La fecha de baja no puede ser anterior a la de alta."))
