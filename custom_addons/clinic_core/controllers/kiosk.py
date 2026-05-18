"""HTTP controllers for the clinic kiosk (self check-in)."""
from datetime import datetime, time

from odoo import fields, http
from odoo.http import request


class ClinicKioskController(http.Controller):

    def _get_kiosk(self, token):
        return (
            request.env["clinic.kiosk"]
            .sudo()
            .search([("token", "=", token), ("active", "=", True)], limit=1)
        )

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

        today = fields.Date.context_today(kiosk)
        today_start = datetime.combine(today, time.min)
        today_end = datetime.combine(today, time.max)
        appts = (
            request.env["clinic.appointment"]
            .sudo()
            .search([
                ("location_id", "=", kiosk.location_id.id),
                ("start_datetime", ">=", today_start),
                ("start_datetime", "<=", today_end),
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
            "appointments": [{
                "id": a.id,
                "time": a.start_datetime.strftime("%H:%M"),
                "practitioner": a.practitioner_id.name or "",
                "practice": (a.practice_id.display_name if a.practice_id else ""),
                "patient": a.patient_id.name or "",
                "state": a.state,
            } for a in appts],
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

        if appt.state in ("checked-in", "arrived"):
            return {
                "already_checked": True,
                "patient": appt.patient_id.name,
                "time": appt.start_datetime.strftime("%H:%M"),
                "practitioner": appt.practitioner_id.name,
            }
        if appt.state == "fulfilled":
            return {"error": "Tu turno ya terminó."}
        if appt.state not in ("pending", "booked"):
            return {"error": "Tu turno no está en estado válido."}

        appt.action_check_in()
        kiosk.last_check_in_at = fields.Datetime.now()
        return {
            "ok": True,
            "patient": appt.patient_id.name,
            "time": appt.start_datetime.strftime("%H:%M"),
            "practitioner": appt.practitioner_id.name,
        }
