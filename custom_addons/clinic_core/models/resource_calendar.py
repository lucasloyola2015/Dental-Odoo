"""Extensions to resource.calendar to support clinic scheduling.

Three pieces:
1. `resource.calendar.attendance` gets an `active` field — soft-toggle per line in the routine grid.
2. `resource.calendar.leaves` gets an `active` field — soft-toggle per excluded period.
3. `resource.calendar` overrides `_work_intervals_batch` to merge in
   `clinic.schedule.extra_day` intervals (non-routine days like substitutions).

Since `active` becomes a model field on attendance/leaves, the default search behavior
automatically excludes inactive rows (no need to add active filters in the existing
`_attendance_intervals_batch` / `_leave_intervals_batch` queries).
"""

from datetime import datetime, time

import pytz

from odoo import api, fields, models
from odoo.tools.intervals import Intervals


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    active = fields.Boolean(
        default=True,
        help=(
            "Soft toggle: si está desactivada, esta franja NO aparece en el cálculo de "
            "disponibilidad de turnos. Útil para suspender temporalmente sin borrar."
        ),
    )

    # Day-of-week short labels in Spanish for auto-naming
    _DOW_ES = {
        "0": "Lun", "1": "Mar", "2": "Mié", "3": "Jue",
        "4": "Vie", "5": "Sáb", "6": "Dom",
    }

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-populate `name` (required, no native default) when not provided.

        Generates e.g. "Lun 09:00-13:00" from dayofweek + hour_from + hour_to.
        Allows the modal's editable list to skip the `name` column entirely.
        """
        for vals in vals_list:
            if not vals.get("name"):
                vals["name"] = self._build_attendance_name(vals)
        return super().create(vals_list)

    def write(self, vals):
        """Keep `name` in sync when dayofweek/hour_from/hour_to change in-place,
        only when (1) the user did not explicitly set a name in this write, and
        (2) the current name appears to be auto-generated (starts with a known
        day prefix). Avoids overwriting user-typed names and prevents recursion.
        """
        res = super().write(vals)
        if "name" in vals:
            return res
        if not any(k in vals for k in ("dayofweek", "hour_from", "hour_to")):
            return res
        for rec in self:
            if not rec.name or rec.name[:3] not in self._DOW_ES.values():
                continue
            expected = rec._build_attendance_name({
                "dayofweek": rec.dayofweek,
                "hour_from": rec.hour_from,
                "hour_to": rec.hour_to,
            })
            if rec.name != expected:
                # Call parent's write directly to skip this branch on the recursion
                super(ResourceCalendarAttendance, rec).write({"name": expected})
        return res

    @api.model
    def _build_attendance_name(self, vals):
        dow = str(vals.get("dayofweek", "0"))
        h_from = vals.get("hour_from") or 0.0
        h_to = vals.get("hour_to") or 0.0
        h_from_str = f"{int(h_from):02d}:{int(round((h_from - int(h_from)) * 60)):02d}"
        h_to_str = f"{int(h_to):02d}:{int(round((h_to - int(h_to)) * 60)):02d}"
        return f"{self._DOW_ES.get(dow, '?')} {h_from_str}-{h_to_str}"


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    active = fields.Boolean(
        default=True,
        help=(
            "Soft toggle: si está desactivado, este período excluido NO bloquea la agenda. "
            "Permite cancelar una exclusión sin borrarla."
        ),
    )


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    extra_day_ids = fields.One2many(
        comodel_name="clinic.schedule.extra_day",
        inverse_name="calendar_id",
        string="Días extras",
        help=(
            "Días puntuales (fuera de la grilla rutinaria) en los que el profesional "
            "atiende — ej. reemplazos temporales."
        ),
    )
    routine_grid_html = fields.Html(
        string="Grilla rutinaria (vista semanal)",
        compute="_compute_routine_grid_html",
        sanitize=False,
        readonly=True,
        help="Vista visual de la grilla rutinaria (solo lectura, se regenera al editar las franjas).",
    )

    @api.depends(
        "attendance_ids.dayofweek",
        "attendance_ids.hour_from",
        "attendance_ids.hour_to",
        "attendance_ids.active",
        "attendance_ids.day_period",
        "attendance_ids.display_type",
    )
    def _compute_routine_grid_html(self):
        """Render a weekly HTML grid (days × time blocks) of active routine attendances.

        Resolution: 30-min slots from 06:00 to 22:00. Inactive attendances and
        section lines are skipped. Lunch periods are skipped too (not work hours).
        """
        DAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        SLOT_MIN = 30
        START_H = 6
        END_H = 22

        slots = []
        h = START_H
        m = 0
        while (h, m) < (END_H, 0):
            slots.append((h, m))
            m += SLOT_MIN
            if m >= 60:
                h += 1
                m -= 60

        def slot_label(h, m):
            return f"{h:02d}:{m:02d}"

        def is_busy(att_list, h, m):
            """A 30-min slot starting at (h, m) is busy if some attendance covers it."""
            slot_start = h + m / 60.0
            slot_end = slot_start + SLOT_MIN / 60.0
            for att in att_list:
                if att.hour_from < slot_end and att.hour_to > slot_start:
                    return True
            return False

        cell_style = (
            "padding:2px 4px;text-align:center;font-size:11px;"
            "border:1px solid #e6e6e6;"
        )
        time_col_style = cell_style + "background:#f7f7f7;color:#666;font-family:monospace;"
        busy_style = cell_style + "background:#1f77b4;color:white;font-weight:500;"
        empty_style = cell_style + "background:#fafafa;color:#bbb;"
        header_style = (
            "padding:6px;text-align:center;font-weight:600;background:#eee;"
            "border:1px solid #d0d0d0;"
        )

        for cal in self:
            # Filter to routine work attendances (active, no section, not lunch)
            atts = cal.attendance_ids.filtered(
                lambda a: a.active and not a.display_type and a.day_period != "lunch"
            )
            # Group by dayofweek for fast lookup
            by_day = {str(d): [] for d in range(7)}
            for att in atts:
                by_day[att.dayofweek].append(att)

            if not atts:
                cal.routine_grid_html = (
                    "<div style='padding:12px;color:#888;font-style:italic;'>"
                    "Sin franjas rutinarias activas. Cargá horarios en el tab 'Grilla rutinaria'."
                    "</div>"
                )
                continue

            html = [
                "<div style='overflow-x:auto;'>",
                "<table style='border-collapse:collapse;width:100%;font-family:sans-serif;'>",
                "<thead><tr>",
                f"<th style='{header_style}width:60px;'>Hora</th>",
            ]
            for i, day in enumerate(DAYS):
                html.append(f"<th style='{header_style}'>{day}</th>")
                if i < len(DAYS) - 1:
                    pass  # no separator needed
            html.append("</tr></thead><tbody>")

            for h, m in slots:
                html.append("<tr>")
                html.append(f"<td style='{time_col_style}'>{slot_label(h, m)}</td>")
                for d in range(7):
                    day_atts = by_day[str(d)]
                    if is_busy(day_atts, h, m):
                        html.append(f"<td style='{busy_style}'>&nbsp;</td>")
                    else:
                        html.append(f"<td style='{empty_style}'>&nbsp;</td>")
                html.append("</tr>")

            html.append("</tbody></table>")
            html.append(
                "<div style='margin-top:8px;font-size:11px;color:#666;'>"
                "Slots de 30 min de 06:00 a 22:00. Solo se muestran franjas <em>activas</em> "
                "de la grilla rutinaria (no incluye días extras ni excluidos)."
                "</div>"
            )
            html.append("</div>")
            cal.routine_grid_html = "".join(html)

    def _work_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None, compute_leaves=True):
        """Override: append clinic.schedule.extra_day intervals to the base result.

        The native call returns `attendance - leaves` per resource. We add active
        extra_days from this calendar that fall within [start_dt, end_dt] on top
        (union). Inactive attendances/leaves are already filtered out by the default
        `active_test` context applied to search().
        """
        result = super()._work_intervals_batch(
            start_dt, end_dt,
            resources=resources, domain=domain, tz=tz, compute_leaves=compute_leaves,
        )

        if not self or len(self) > 1:
            # super() requires ensure_one for attendance computation; nothing to merge
            return result

        extras = self.env["clinic.schedule.extra_day"].search([
            ("calendar_id", "=", self.id),
            ("date", ">=", start_dt.date()),
            ("date", "<=", end_dt.date()),
        ])
        if not extras:
            return result

        cal_tz = pytz.timezone(self.tz or "UTC")
        extra_tuples = []
        for extra in extras:
            d = extra.date
            h_from = extra.hour_from or 0.0
            h_to = extra.hour_to or 0.0
            # float HH.MM → time
            t_from = time(int(h_from), int(round((h_from - int(h_from)) * 60)))
            t_to = time(int(h_to), int(round((h_to - int(h_to)) * 60))) if h_to < 24 else time(23, 59, 59)
            dt_from = cal_tz.localize(datetime.combine(d, t_from))
            dt_to = cal_tz.localize(datetime.combine(d, t_to))
            extra_tuples.append((dt_from, dt_to, extra))

        extra_intervals = Intervals(extra_tuples)

        # Union extras into every resource's intervals
        for key in result:
            result[key] = result[key] | extra_intervals
        return result
