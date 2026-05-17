from odoo import _, api, fields, models


class ClinicPatient(models.Model):
    _inherit = "clinic.patient"

    dental_tooth_state_ids = fields.One2many(
        comodel_name="clinic.dental.tooth.state",
        inverse_name="patient_id",
        string="Estado del odontograma",
    )
    dental_affected_teeth_count = fields.Integer(
        string="Piezas con estado",
        compute="_compute_dental_affected_teeth_count",
        help="Cantidad de piezas dentarias con al menos un estado registrado (sano = sin registro).",
    )

    @api.depends("dental_tooth_state_ids.tooth_id")
    def _compute_dental_affected_teeth_count(self):
        for rec in self:
            rec.dental_affected_teeth_count = len(
                rec.dental_tooth_state_ids.mapped("tooth_id")
            )

    def action_view_dental_chart(self):
        """Open the patient's tooth-state list, filtered to this patient."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Odontograma — %s") % self.name,
            "res_model": "clinic.dental.tooth.state",
            "view_mode": "list,form",
            "domain": [("patient_id", "=", self.id)],
            "context": {"default_patient_id": self.id},
        }
