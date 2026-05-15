from datetime import datetime, timedelta, time

from odoo import api, fields, models


class ClinicDashboard(models.TransientModel):
    _name = "clinic.dashboard"
    _description = "Dashboard de la secretaría"

    # -------------------------------------------------------------------------
    # KPIs (computed integers)
    # -------------------------------------------------------------------------
    appointments_today_count = fields.Integer(
        string="Turnos hoy", compute="_compute_kpis"
    )
    appointments_pending_count = fields.Integer(
        string="Sin confirmar", compute="_compute_kpis"
    )
    appointments_week_count = fields.Integer(
        string="Próx. 7 días", compute="_compute_kpis"
    )
    new_patients_month_count = fields.Integer(
        string="Nuevos pacientes (30d)", compute="_compute_kpis"
    )
    noshows_30d_count = fields.Integer(
        string="No-shows (30d)", compute="_compute_kpis"
    )

    # -------------------------------------------------------------------------
    # Computed Many2many lists (more flexible than One2many for compute)
    # -------------------------------------------------------------------------
    today_appointment_ids = fields.Many2many(
        comodel_name="clinic.appointment",
        relation="clinic_dashboard_today_appt_rel",
        column1="dashboard_id",
        column2="appointment_id",
        string="Agenda de hoy",
        compute="_compute_lists",
    )
    pending_appointment_ids = fields.Many2many(
        comodel_name="clinic.appointment",
        relation="clinic_dashboard_pending_appt_rel",
        column1="dashboard_id",
        column2="appointment_id",
        string="Pendientes de confirmación",
        compute="_compute_lists",
    )

    # -------------------------------------------------------------------------
    # Helper: time windows
    # -------------------------------------------------------------------------
    @api.model
    def _time_windows(self):
        today = fields.Date.context_today(self)
        today_start = datetime.combine(today, time.min)
        return {
            "today_start": today_start,
            "today_end": today_start + timedelta(days=1),
            "week_end": today_start + timedelta(days=7),
            "month_ago": today_start - timedelta(days=30),
        }

    @api.model
    def _company_domain(self):
        return [("company_id", "in", self.env.companies.ids)]

    # -------------------------------------------------------------------------
    # Computes
    # -------------------------------------------------------------------------
    @api.depends_context("uid", "allowed_company_ids")
    def _compute_kpis(self):
        Appointment = self.env["clinic.appointment"]
        Patient = self.env["clinic.patient"]
        w = self._time_windows()
        company_dom = self._company_domain()

        for rec in self:
            rec.appointments_today_count = Appointment.search_count(company_dom + [
                ("start_datetime", ">=", w["today_start"]),
                ("start_datetime", "<", w["today_end"]),
                ("state", "not in", ("cancelled", "entered-in-error")),
            ])
            rec.appointments_pending_count = Appointment.search_count(company_dom + [
                ("state", "=", "pending"),
                ("start_datetime", ">=", w["today_start"]),
                ("start_datetime", "<", w["week_end"]),
            ])
            rec.appointments_week_count = Appointment.search_count(company_dom + [
                ("start_datetime", ">=", w["today_start"]),
                ("start_datetime", "<", w["week_end"]),
                ("state", "not in", ("cancelled", "noshow", "entered-in-error")),
            ])
            rec.new_patients_month_count = Patient.search_count(company_dom + [
                ("create_date", ">=", w["month_ago"]),
            ])
            rec.noshows_30d_count = Appointment.search_count(company_dom + [
                ("state", "=", "noshow"),
                ("start_datetime", ">=", w["month_ago"]),
            ])

    @api.depends_context("uid", "allowed_company_ids")
    def _compute_lists(self):
        Appointment = self.env["clinic.appointment"]
        w = self._time_windows()
        company_dom = self._company_domain()

        today_appts = Appointment.search(company_dom + [
            ("start_datetime", ">=", w["today_start"]),
            ("start_datetime", "<", w["today_end"]),
            ("state", "not in", ("cancelled", "entered-in-error")),
        ], order="start_datetime asc")

        pending = Appointment.search(company_dom + [
            ("state", "=", "pending"),
            ("start_datetime", ">=", w["today_start"]),
            ("start_datetime", "<", w["week_end"]),
        ], order="start_datetime asc", limit=20)

        for rec in self:
            rec.today_appointment_ids = today_appts
            rec.pending_appointment_ids = pending

    # -------------------------------------------------------------------------
    # KPI click-throughs (open filtered appointment list)
    # -------------------------------------------------------------------------
    def _open_appointment_action(self, name, domain, context=None):
        action = self.env["ir.actions.actions"]._for_xml_id("clinic_core.action_clinic_appointment")
        action.update({
            "name": name,
            "domain": domain,
            "context": context or {},
        })
        return action

    def action_open_today(self):
        w = self._time_windows()
        return self._open_appointment_action(
            "Turnos de hoy",
            [
                ("start_datetime", ">=", w["today_start"]),
                ("start_datetime", "<", w["today_end"]),
                ("state", "not in", ("cancelled", "entered-in-error")),
            ],
        )

    def action_open_pending(self):
        w = self._time_windows()
        return self._open_appointment_action(
            "Turnos pendientes de confirmar",
            [
                ("state", "=", "pending"),
                ("start_datetime", ">=", w["today_start"]),
                ("start_datetime", "<", w["week_end"]),
            ],
        )

    def action_open_week(self):
        w = self._time_windows()
        return self._open_appointment_action(
            "Próximos 7 días",
            [
                ("start_datetime", ">=", w["today_start"]),
                ("start_datetime", "<", w["week_end"]),
                ("state", "not in", ("cancelled", "noshow", "entered-in-error")),
            ],
        )

    def action_open_noshows(self):
        w = self._time_windows()
        return self._open_appointment_action(
            "No-shows últimos 30 días",
            [
                ("state", "=", "noshow"),
                ("start_datetime", ">=", w["month_ago"]),
            ],
        )

    def action_open_new_patients(self):
        w = self._time_windows()
        return {
            "type": "ir.actions.act_window",
            "name": "Pacientes nuevos (30 días)",
            "res_model": "clinic.patient",
            "view_mode": "list,form",
            "domain": [("create_date", ">=", w["month_ago"])],
            "context": {},
        }

    # -------------------------------------------------------------------------
    # Quick actions (top buttons)
    # -------------------------------------------------------------------------
    def action_new_appointment(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Nuevo turno",
            "res_model": "clinic.appointment",
            "view_mode": "form",
            "target": "current",
            "context": {},
        }

    def action_new_patient(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Nuevo paciente",
            "res_model": "clinic.patient",
            "view_mode": "form",
            "target": "current",
            "context": {},
        }

    def action_search_patient(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Pacientes",
            "res_model": "clinic.patient",
            "view_mode": "list,form",
            "target": "current",
        }

    def action_full_agenda(self):
        action = self.env["ir.actions.actions"]._for_xml_id("clinic_core.action_clinic_appointment")
        action["view_mode"] = "calendar,list,form"
        return action

    def action_search_availability(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Buscar disponibilidad",
            "res_model": "clinic.appointment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {},
        }

    # -------------------------------------------------------------------------
    # Charts (open graph/pivot of clinic.appointment with preset groupbys)
    # -------------------------------------------------------------------------
    def _open_appointment_chart(self, name, groupbys, domain=None):
        w = self._time_windows()
        default_domain = [("start_datetime", ">=", w["month_ago"])]
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "clinic.appointment",
            "view_mode": "graph,pivot,list",
            "domain": domain or default_domain,
            "context": {
                "graph_groupbys": groupbys,
                "graph_measure": "__count__",
                "pivot_row_groupby": groupbys,
                "pivot_measures": ["__count__"],
            },
        }

    def action_chart_by_state(self):
        return self._open_appointment_chart(
            "Turnos por estado",
            ["state"],
        )

    def action_chart_by_day(self):
        return self._open_appointment_chart(
            "Turnos por día",
            ["start_datetime:day"],
        )

    def action_chart_by_practitioner(self):
        return self._open_appointment_chart(
            "Turnos por profesional",
            ["practitioner_id"],
        )

    def action_chart_by_insurance(self):
        return self._open_appointment_chart(
            "Turnos por obra social",
            ["coverage_id"],
        )

    # -------------------------------------------------------------------------
    # Entry point: action_open opens a fresh dashboard
    # -------------------------------------------------------------------------
    @api.model
    def action_open_dashboard(self):
        record = self.create({})
        return {
            "type": "ir.actions.act_window",
            "name": "Dashboard Clínica",
            "res_model": "clinic.dashboard",
            "view_mode": "form",
            "res_id": record.id,
            "target": "current",
            "context": {"create": False, "edit": False, "delete": False},
        }
