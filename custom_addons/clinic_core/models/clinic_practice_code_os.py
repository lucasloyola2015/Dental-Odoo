from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicPracticeCodeOS(models.Model):
    _name = "clinic.practice.code.os"
    _description = "Código alternativo de una obra social para una práctica FACO"
    _order = "health_insurance_id, practice_id, valid_from desc"
    _rec_name = "display_name"

    practice_id = fields.Many2one(
        comodel_name="clinic.practice",
        string="Práctica (FACO)",
        required=True,
        ondelete="cascade",
        index=True,
    )
    health_insurance_id = fields.Many2one(
        comodel_name="clinic.health.insurance",
        string="Obra social",
        required=True,
        ondelete="cascade",
        index=True,
    )
    os_code = fields.Char(
        string="Código OS",
        required=True,
        help="Código que usa la obra social para esta práctica. Ej: AVALIAN usa '346027' para Cefalometría.",
    )
    os_name = fields.Char(
        string="Nombre OS",
        help="Nombre que usa la OS si difiere del Colegio.",
    )
    valid_from = fields.Date(string="Vigente desde", required=True, default=fields.Date.context_today)
    notes = fields.Text(string="Notas")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        index=True,
        help="Vacío = mapeo compartido (los códigos de AVALIAN son nacionales).",
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)

    _unique_mapping = models.Constraint(
        "unique (practice_id, health_insurance_id, valid_from, company_id)",
        "Ya existe un mapeo de código para esa práctica/OS/fecha en este alcance.",
    )

    @api.depends("practice_id", "health_insurance_id", "os_code")
    def _compute_display_name(self):
        for rec in self:
            os = rec.health_insurance_id.code or "?"
            prac = rec.practice_id.faco_code or "?"
            rec.display_name = f"{os}: {prac} → {rec.os_code or '?'}"
