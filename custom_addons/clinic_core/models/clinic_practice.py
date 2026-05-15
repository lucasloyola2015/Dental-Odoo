from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicPractice(models.Model):
    _name = "clinic.practice"
    _description = "Práctica clínica (catálogo FACO)"
    _order = "faco_code, name"
    _rec_name = "display_name"

    faco_code = fields.Char(
        string="Código FACO",
        required=True,
        index=True,
        help="Código del Colegio en formato CC.SS.NN o CC.NN. Ej: 01.01, 04.01.04.",
    )
    faco_chapter = fields.Integer(
        string="Capítulo",
        compute="_compute_faco_parts",
        store=True,
        help="Número de capítulo extraído del código (1-12 según FACO).",
    )
    faco_subchapter = fields.Char(
        string="Sub-capítulo",
        compute="_compute_faco_parts",
        store=True,
    )
    name = fields.Char(string="Nombre", required=True, translate=True)
    short_name = fields.Char(string="Nombre corto", help="Versión breve para listados.")
    description = fields.Text(string="Descripción detallada")
    slots_required = fields.Integer(
        string="Slots requeridos",
        default=2,
        help="Cantidad de slots de 15 min que ocupa la práctica. 2 = 30 min, 4 = 60 min.",
    )
    is_new_code = fields.Boolean(
        string="Código nuevo",
        help="Marcado con '*' en el PDF de FACO (códigos nuevos del nomenclador).",
    )
    is_to_be_arranged = fields.Boolean(
        string="A convenir",
        help="True si la práctica no tiene tarifario fijo y se acuerda caso a caso.",
    )
    specialty_id = fields.Many2one(
        comodel_name="clinic.specialty",
        string="Especialidad sugerida",
        help="Especialidad principal asociada a la práctica (no es regla, solo hint).",
    )
    observations = fields.Text(
        string="Observaciones",
        help=(
            "Notas del Colegio sobre la práctica. "
            "Ej: 'Esta práctica no contempla gastos de envío de mecánica dental.'"
        ),
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        index=True,
        help="Vacío = práctica compartida entre todas las compañías (catálogo nacional FACO).",
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("faco_code")
    def _compute_faco_parts(self):
        for rec in self:
            if not rec.faco_code:
                rec.faco_chapter = 0
                rec.faco_subchapter = False
                continue
            parts = rec.faco_code.split(".")
            try:
                rec.faco_chapter = int(parts[0])
            except (ValueError, IndexError):
                rec.faco_chapter = 0
            rec.faco_subchapter = parts[1] if len(parts) >= 3 else False

    @api.depends("faco_code", "name")
    def _compute_display_name(self):
        for rec in self:
            if rec.faco_code and rec.name:
                rec.display_name = f"{rec.faco_code} — {rec.name}"
            else:
                rec.display_name = rec.name or rec.faco_code or "?"

    @api.constrains("faco_code", "company_id")
    def _check_faco_code_unique(self):
        for rec in self:
            domain = [("id", "!=", rec.id), ("faco_code", "=", rec.faco_code)]
            if rec.company_id:
                domain.append(("company_id", "in", (False, rec.company_id.id)))
            else:
                domain.append(("company_id", "=", False))
            if self.with_context(active_test=False).search_count(domain):
                raise ValidationError(
                    _("Ya existe una práctica con el código FACO %s en este alcance.") % rec.faco_code
                )
