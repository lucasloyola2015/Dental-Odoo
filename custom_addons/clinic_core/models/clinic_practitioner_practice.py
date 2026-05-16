from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicPractitionerPractice(models.Model):
    """Práctica que un profesional realiza en una sede física, con precio particular
    y duración override por sede.

    Refactor 2026-05-16: company_id reemplazado por location_id (decisión P).
    El profe puede tener precios distintos por sede (ej. en Roldán $X, en Funes $Y).
    """

    _name = "clinic.practitioner.practice"
    _description = "Práctica que realiza un profesional en una sede (con override de precio y duración)"
    _order = "employee_id, practice_id"
    _rec_name = "display_name"

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
    location_id = fields.Many2one(
        comodel_name="clinic.location",
        string="Sucursal",
        required=True,
        ondelete="restrict",
        index=True,
        help="Sede física donde el profesional realiza esta práctica a este precio.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        related="location_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )
    can_perform = fields.Boolean(
        string="Realiza",
        default=True,
        help="Marca si el profesional efectivamente realiza esta práctica en esta sede.",
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

    _employee_practice_location_unique = models.Constraint(
        "unique (employee_id, practice_id, location_id)",
        "Esta práctica ya está cargada para el profesional en esta sede.",
    )

    @api.depends("employee_id.name", "practice_id.faco_code", "practice_id.name", "location_id.code")
    def _compute_display_name(self):
        for rec in self:
            emp = rec.employee_id.name or "?"
            prac = rec.practice_id.display_name or "?"
            loc = rec.location_id.code or "?"
            rec.display_name = f"{emp} — {prac} @ {loc}"
