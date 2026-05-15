from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicSpecialty(models.Model):
    _name = "clinic.specialty"
    _description = "Especialidad clínica"
    _order = "complete_name"
    _rec_name = "complete_name"
    _parent_store = True

    name = fields.Char(string="Nombre", required=True, translate=True)
    code = fields.Char(
        string="Código",
        required=True,
        help="Código corto identificador. Ej: ODONTO, ORTOD.",
    )
    parent_id = fields.Many2one(
        comodel_name="clinic.specialty",
        string="Especialidad padre",
        ondelete="restrict",
        index=True,
        help="Especialidad de la que esta es una rama. Vacío = especialidad raíz.",
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        comodel_name="clinic.specialty",
        inverse_name="parent_id",
        string="Sub-especialidades",
    )
    complete_name = fields.Char(
        string="Nombre completo",
        compute="_compute_complete_name",
        store=True,
        recursive=True,
        help="Ruta completa, ej: 'Odontología / Ortodoncia'.",
    )
    default_appointment_duration_minutes = fields.Integer(
        string="Duración default de turno (min)",
        default=30,
        help=(
            "Duración por defecto aplicada al agendar un turno cuando el profesional "
            "no definió la suya. La secretaria puede editarla caso a caso."
        ),
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        index=True,
        help="Vacío = especialidad compartida entre todas las compañías.",
    )

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id:
                rec.complete_name = f"{rec.parent_id.complete_name} / {rec.name}"
            else:
                rec.complete_name = rec.name

    @api.constrains("parent_id")
    def _check_specialty_recursion(self):
        if self._has_cycle():
            raise ValidationError(_("La jerarquía de especialidades no puede ser recursiva."))

    @api.constrains("code", "company_id")
    def _check_code_unique(self):
        for rec in self:
            domain = [("id", "!=", rec.id), ("code", "=", rec.code)]
            if rec.company_id:
                domain.append(("company_id", "in", (False, rec.company_id.id)))
            else:
                domain.append(("company_id", "=", False))
            if self.with_context(active_test=False).search_count(domain):
                raise ValidationError(
                    _("Ya existe una especialidad con el código %s en este alcance.") % rec.code
                )
