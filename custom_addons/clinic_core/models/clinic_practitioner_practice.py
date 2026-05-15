from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicPractitionerPractice(models.Model):
    _name = "clinic.practitioner.practice"
    _description = "Práctica que realiza un profesional (con override de precio y duración)"
    _order = "employee_id, practice_id"
    _rec_name = "display_name"
    _check_company_auto = True

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Profesional",
        required=True,
        ondelete="cascade",
        index=True,
        domain="[('is_clinic_practitioner', '=', True)]",
    )
    practice_id = fields.Many2one(
        comodel_name="clinic.practice",
        string="Práctica",
        required=True,
        ondelete="restrict",
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    can_perform = fields.Boolean(
        string="Realiza",
        default=True,
        help="Marca si el profesional efectivamente realiza esta práctica en esta compañía.",
    )
    price_particular = fields.Float(
        string="Precio particular ($)",
        digits="Product Price",
        help="Precio que cobra el profesional cuando el paciente es particular (sin obra social).",
    )
    default_duration_minutes = fields.Integer(
        string="Duración (min)",
        help=(
            "Override de la duración del turno para esta práctica específica. "
            "Si está vacío, usa la cascada general (profesional → especialidad → 30 min)."
        ),
    )
    notes = fields.Text(string="Notas")
    active = fields.Boolean(default=True)
    display_name = fields.Char(compute="_compute_display_name", store=True)

    _employee_practice_company_unique = models.Constraint(
        "unique (employee_id, practice_id, company_id)",
        "Esta práctica ya está cargada para el profesional en esta compañía.",
    )

    @api.depends("employee_id.name", "practice_id.faco_code", "practice_id.name")
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or "?"
            prac = rec.practice_id.display_name or "?"
            rec.display_name = f"{emp} — {prac}"
