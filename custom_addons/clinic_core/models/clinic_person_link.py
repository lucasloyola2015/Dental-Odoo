from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


INVERSE_TYPE = {
    "parent": "child",
    "child": "parent",
    "spouse": "spouse",
    "partner": "partner",
    "sibling": "sibling",
    "legal_guardian": "ward",
    "ward": "legal_guardian",
    "responsible": "dependent",
    "dependent": "responsible",
    "grandparent": "grandchild",
    "grandchild": "grandparent",
    "relative": "relative",
    "other": "other",
}

# Fields that are synced between original and mirror (semantic equality)
_SYNC_FIELDS = ("valid_from", "valid_to", "notes")


class ClinicPersonLink(models.Model):
    _name = "clinic.person.link"
    _description = "Vínculo humano entre dos personas (bidireccional)"
    _order = "id"
    _rec_name = "display_name"

    partner_a_id = fields.Many2one(
        comodel_name="res.partner",
        string="Persona A",
        required=True,
        ondelete="cascade",
        index=True,
        domain="[('is_clinic_person', '=', True)]",
    )
    partner_b_id = fields.Many2one(
        comodel_name="res.partner",
        string="Persona B",
        required=True,
        ondelete="cascade",
        index=True,
        domain="[('is_clinic_person', '=', True)]",
    )
    relationship_type = fields.Selection(
        selection=[
            ("parent", "Padre/Madre"),
            ("child", "Hijo/Hija"),
            ("spouse", "Cónyuge"),
            ("partner", "Pareja"),
            ("sibling", "Hermano/a"),
            ("legal_guardian", "Tutor legal"),
            ("ward", "Tutelado/a"),
            ("responsible", "Responsable"),
            ("dependent", "Dependiente"),
            ("grandparent", "Abuelo/a"),
            ("grandchild", "Nieto/a"),
            ("relative", "Familiar"),
            ("other", "Otro"),
        ],
        string="A es ... de B",
        required=True,
        help="Tipo de relación de A hacia B. El sistema crea automáticamente el vínculo inverso.",
    )
    relationship_type_other = fields.Char(
        string="Especificar otro",
        help="Si el tipo de vínculo es 'Otro', indicar acá la descripción.",
    )
    # Flags: lo que A puede hacer sobre B (NO se sincronizan al mirror — cada lado los gestiona)
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
    valid_from = fields.Date(string="Vigente desde", default=fields.Date.context_today)
    valid_to = fields.Date(string="Vigente hasta")
    notes = fields.Text(string="Notas")
    mirror_id = fields.Many2one(
        comodel_name="clinic.person.link",
        string="Vínculo espejo",
        ondelete="set null",
        copy=False,
        readonly=True,
        help="Referencia al vínculo inverso (auto-creado).",
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("partner_a_id.display_name", "partner_b_id.display_name", "relationship_type", "relationship_type_other")
    def _compute_display_name(self):
        type_labels = dict(self._fields["relationship_type"].selection)
        for rec in self:
            rel = rec.relationship_type_other if rec.relationship_type == "other" else type_labels.get(rec.relationship_type, "?")
            rec.display_name = f"{rec.partner_a_id.display_name or '?'} → {rel} → {rec.partner_b_id.display_name or '?'}"

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

    @api.constrains("valid_to", "valid_from")
    def _check_dates(self):
        for rec in self:
            if rec.valid_to and rec.valid_from and rec.valid_to < rec.valid_from:
                raise ValidationError(_("Vigente hasta no puede ser anterior a Vigente desde."))

    # -------------------------------------------------------------------------
    # Bidirectional auto-management
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env.context.get("_creating_mirror"):
            return records

        for orig in records:
            if orig.mirror_id:
                continue  # Already paired (defensive)
            inverse_type = INVERSE_TYPE.get(orig.relationship_type, orig.relationship_type)
            mirror = self.with_context(_creating_mirror=True).create([{
                "partner_a_id": orig.partner_b_id.id,
                "partner_b_id": orig.partner_a_id.id,
                "relationship_type": inverse_type,
                "relationship_type_other": orig.relationship_type_other if inverse_type == "other" else False,
                "valid_from": orig.valid_from,
                "valid_to": orig.valid_to,
                "notes": orig.notes,
                # flags start fresh — each side manages its own
            }])
            # Pair both ways
            orig.mirror_id = mirror.id
            mirror.mirror_id = orig.id
        return records

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get("_syncing_mirror"):
            return res

        # Sync semantic fields to mirror
        sync_vals = {k: v for k, v in vals.items() if k in _SYNC_FIELDS}
        # If relationship_type changes, mirror gets the inverse
        if "relationship_type" in vals:
            inverse = INVERSE_TYPE.get(vals["relationship_type"], vals["relationship_type"])
            sync_vals["relationship_type"] = inverse
        if "relationship_type_other" in vals:
            sync_vals["relationship_type_other"] = vals["relationship_type_other"]

        if sync_vals:
            mirrors = self.mapped("mirror_id").filtered(lambda m: m)
            if mirrors:
                mirrors.with_context(_syncing_mirror=True).write(sync_vals)
        return res

    def unlink(self):
        if self.env.context.get("_deleting_mirror"):
            return super().unlink()
        # Collect mirrors that aren't already in the deletion set
        mirrors = self.mapped("mirror_id").filtered(lambda m: m and m not in self)
        res = super().unlink()
        if mirrors:
            mirrors.with_context(_deleting_mirror=True).unlink()
        return res
