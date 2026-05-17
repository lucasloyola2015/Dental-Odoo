from odoo import _, api, fields, models


class ClinicDentalToothState(models.Model):
    """Estado actual de una pieza dentaria de un paciente.

    Una fila por (paciente, pieza). Cuando el odontólogo registra un cambio
    (caries → obturada, por ejemplo), el `last_updated` se setea automático.
    V1 = sólo estado actual; histórico de cambios queda diferido a V2.
    """

    _name = "clinic.dental.tooth.state"
    _description = "Estado de una pieza dentaria del paciente"
    _order = "patient_id, tooth_id"
    _rec_name = "display_name"

    patient_id = fields.Many2one(
        comodel_name="clinic.patient",
        string="Paciente",
        required=True,
        ondelete="cascade",
        index=True,
    )
    tooth_id = fields.Many2one(
        comodel_name="clinic.dental.tooth",
        string="Pieza",
        required=True,
        ondelete="restrict",
        index=True,
    )
    state = fields.Selection(
        selection=[
            ("healthy", "Sana"),
            ("caries", "Caries"),
            ("restored", "Obturada"),
            ("endodontic", "Endodonciada"),
            ("crown", "Corona"),
            ("bridge", "Puente"),
            ("implant", "Implante"),
            ("prosthesis", "Prótesis"),
            ("extracted", "Extraída"),
            ("missing", "Ausente (no erupcionó)"),
            ("root_fragment", "Resto radicular"),
            ("to_extract", "A extraer"),
        ],
        string="Estado",
        default="healthy",
        required=True,
        tracking=True,
    )
    notes = fields.Text(string="Notas clínicas")
    last_updated = fields.Datetime(
        string="Última actualización",
        default=fields.Datetime.now,
        readonly=True,
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)

    _patient_tooth_unique = models.Constraint(
        "unique (patient_id, tooth_id)",
        "Este paciente ya tiene un estado registrado para esta pieza.",
    )

    @api.depends("patient_id.name", "tooth_id.fdi_code", "state")
    def _compute_display_name(self):
        state_dict = dict(self._fields["state"].selection)
        for rec in self:
            code = rec.tooth_id.fdi_code or "?"
            label = state_dict.get(rec.state, "?")
            rec.display_name = f"{code} — {label}"

    def write(self, vals):
        if any(k in vals for k in ("state", "notes")):
            vals["last_updated"] = fields.Datetime.now()
        return super().write(vals)
