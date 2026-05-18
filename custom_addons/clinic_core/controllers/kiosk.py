"""HTTP controllers for the clinic kiosk (self check-in).

All date/time math is done in the kiosk's location timezone. Internally,
Odoo stores datetimes as naive UTC; we convert at the boundary so the
user-facing values (and "minutes until appointment") are always in local
time.
"""
from datetime import datetime, time, timedelta

import pytz

from odoo import fields, http
from odoo.http import request


class ClinicKioskController(http.Controller):

    def _get_kiosk(self, token):
        return (
            request.env["clinic.kiosk"]
            .sudo()
            .search([("token", "=", token), ("active", "=", True)], limit=1)
        )

    def _kiosk_tz(self, kiosk):
        return pytz.timezone(kiosk.location_id.tz or "America/Argentina/Buenos_Aires")

    def _utc_naive(self, local_dt):
        """Strip tzinfo after converting to UTC, so it can be compared to Odoo's
        naive UTC datetimes in the ORM."""
        return local_dt.astimezone(pytz.UTC).replace(tzinfo=None)

    def _appt_to_dict(self, appt, tz, now_local):
        """Serialize an appointment with local-time fields + minutes_until."""
        start_utc = pytz.UTC.localize(appt.start_datetime)
        start_local = start_utc.astimezone(tz)
        delta_min = int((start_local - now_local).total_seconds() // 60)
        return {
            "id": appt.id,
            "time": start_local.strftime("%H:%M"),
            "date": start_local.strftime("%Y-%m-%d"),
            "practitioner": appt.practitioner_id.name or "",
            "practice": (appt.practice_id.display_name if appt.practice_id else ""),
            "patient": appt.patient_id.name or "",
            "state": appt.state,
            "minutes_until": delta_min,
        }

    # ----------------------------- Page render -----------------------------
    @http.route(
        "/kiosk/<string:token>",
        type="http",
        auth="public",
        website=False,
        csrf=False,
        sitemap=False,
    )
    def kiosk_page(self, token, **_):
        kiosk = self._get_kiosk(token)
        if not kiosk:
            return request.not_found()
        return request.render("clinic_core.kiosk_page", {
            "kiosk": kiosk,
            "token": token,
        })

    # ----------------------------- Lookup ----------------------------------
    @http.route(
        "/kiosk/<string:token>/lookup",
        type="json",
        auth="public",
        csrf=False,
    )
    def kiosk_lookup(self, token, dni=None, **_):
        kiosk = self._get_kiosk(token)
        if not kiosk:
            return {"error": "Kiosko inválido."}
        dni = (dni or "").strip()
        if not dni:
            return {"error": "Ingresá tu DNI."}

        tz = self._kiosk_tz(kiosk)
        now_local = datetime.now(tz)
        today_local = now_local.date()
        today_start_local = tz.localize(datetime.combine(today_local, time.min))
        today_end_local = tz.localize(datetime.combine(today_local, time.max))

        appts = (
            request.env["clinic.appointment"]
            .sudo()
            .search([
                ("location_id", "=", kiosk.location_id.id),
                ("start_datetime", ">=", self._utc_naive(today_start_local)),
                ("start_datetime", "<=", self._utc_naive(today_end_local)),
                ("state", "in", ("pending", "booked", "checked-in", "arrived")),
                ("patient_id.vat", "=", dni),
            ], order="start_datetime")
        )

        if not appts:
            return {
                "error": "No encontramos un turno para hoy con ese DNI. "
                         "Pasá por secretaría."
            }

        return {
            "appointments": [self._appt_to_dict(a, tz, now_local) for a in appts],
        }

    # ----------------------------- Confirm ---------------------------------
    @http.route(
        "/kiosk/<string:token>/confirm",
        type="json",
        auth="public",
        csrf=False,
    )
    def kiosk_confirm(self, token, appointment_id=None, **_):
        kiosk = self._get_kiosk(token)
        if not kiosk:
            return {"error": "Kiosko inválido."}
        if not appointment_id:
            return {"error": "Falta el turno."}

        appt = request.env["clinic.appointment"].sudo().browse(int(appointment_id))
        if not appt.exists() or appt.location_id != kiosk.location_id:
            return {"error": "Turno no encontrado."}

        tz = self._kiosk_tz(kiosk)
        now_local = datetime.now(tz)

        if appt.state == "fulfilled":
            return {"error": "Tu turno ya terminó."}
        if appt.state not in ("pending", "booked", "checked-in", "arrived"):
            return {"error": "Tu turno no está en estado válido."}

        already = appt.state in ("checked-in", "arrived")
        if not already:
            appt.action_check_in()
            kiosk.last_check_in_at = fields.Datetime.now()

        info = self._appt_to_dict(appt, tz, now_local)
        info["already_checked"] = already
        info["ok"] = True
        return info
