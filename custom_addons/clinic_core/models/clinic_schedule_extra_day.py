"""Día extra de atención para un profesional en una sede.

Modela un día puntual (no recurrente) en el que el profesional atiende fuera de su
grilla rutinaria — típicamente reemplazos temporales de otro profesional o
disponibilidades excepcionales.

Cuelga del `resource.calendar` del role (a través de `calendar_id`). El override
de `resource.calendar._work_intervals_batch` los mergea en el cómputo de
availability slots.
"""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicScheduleExtraDay(models.Model):
    _name = "clinic.schedule.extra_day"
    _description = "Día extra de atención (fuera de grilla rutinaria)"
    _order = "date, hour_from"
    _rec_name = "display_name"

    calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Calendario",
        required=True,
        ondelete="cascade",
        index=True,
    )
    date = fields.Date(
        string="Fecha",
        required=True,
        help="Día puntual en el que se habilita la atención.",
    )
    hour_from = fields.Float(
        string="Inicio",
        required=True,
        help="Hora de inicio (formato HH:MM, 24h).",
    )
    hour_to = fields.Float(
        string="Fin",
        required=True,
        help="Hora de fin (formato HH:MM, 24h).",
    )
    name = fields.Char(
        string="Motivo",
        help='Ej: "Reemplazo Dr. Soto", "Disponibilidad excepcional".',
    )
    active = fields.Boolean(
        default=True,
        help="Soft toggle: si está desactivado, este día extra NO se considera en la agenda.",
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)

    _hour_order = models.Constraint(
        "check (hour_to > hour_from)",
        "La hora de fin debe ser posterior a la hora de inicio.",
    )
    _hour_range = models.Constraint(
        "check (hour_from >= 0 AND hour_from < 24 AND hour_to > 0 AND hour_to <= 24)",
        "Las horas deben estar entre 0 y 24.",
    )

    @api.depends("date", "hour_from", "hour_to", "name")
    def _compute_display_name(self):
        for rec in self:
            if not rec.date:
                rec.display_name = rec.name or "Día extra"
                continue
            h_from = f"{int(rec.hour_from):02d}:{int(round((rec.hour_from - int(rec.hour_from)) * 60)):02d}"
            h_to = f"{int(rec.hour_to):02d}:{int(round((rec.hour_to - int(rec.hour_to)) * 60)):02d}"
            base = f"{rec.date.strftime('%d/%m/%Y')} {h_from}-{h_to}"
            rec.display_name = f"{base} — {rec.name}" if rec.name else base

    @api.onchange("hour_from", "hour_to")
    def _onchange_hours(self):
        """Mirror the native attendance behavior: clamp + keep order."""
        if self.hour_from is not None:
            self.hour_from = max(0.0, min(self.hour_from, 23.99))
        if self.hour_to is not None:
            self.hour_to = max(0.0, min(self.hour_to, 24.0))
            self.hour_to = max(self.hour_to, self.hour_from or 0.0)
