from odoo import api, fields, models


class ClinicDentalToothState(models.Model):
    """Estado de una superficie dentaria del paciente, con polaridad observado/realizado.

    Una fila por (paciente, pieza, superficie, fase). La 'fase' distingue lo que el
    odontólogo *observa o planifica* (rojo en el odontograma) de lo que ya *está
    ejecutado* (azul). Una misma superficie puede tener ambas filas en simultáneo
    (ej: caries observada + obturación prevista).

    "Sana" no es un estado: significa simplemente que no hay fila.
    """

    _name = "clinic.dental.tooth.state"
    _description = "Estado de una superficie dentaria del paciente"
    _order = "patient_id, tooth_id, surface, phase"
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
    surface = fields.Selection(
        selection=[
            ("occlusal", "Oclusal / Incisal"),
            ("mesial", "Mesial"),
            ("distal", "Distal"),
            ("buccal", "Vestibular"),
            ("lingual", "Lingual / Palatino"),
        ],
        string="Superficie",
        required=True,
        default="occlusal",
        help=(
            "Cara del diente. Oclusal/Incisal es la cara masticatoria; "
            "mesial/distal son las laterales hacia la línea media o hacia atrás; "
            "vestibular hacia el labio/mejilla; lingual/palatino hacia la lengua o paladar."
        ),
    )
    phase = fields.Selection(
        selection=[
            ("planned", "Observado / Previsto (rojo)"),
            ("realized", "Realizado / Existente (azul)"),
        ],
        string="Fase",
        required=True,
        default="planned",
        help=(
            "Fase clínica: 'observado/previsto' es lo que el odontólogo diagnostica "
            "o planifica (se pinta rojo). 'Realizado/existente' es lo ya ejecutado "
            "o presente desde antes (se pinta azul)."
        ),
    )
    state = fields.Selection(
        selection=[
            ("caries", "Caries"),
            ("restoration", "Obturación"),
            ("endodontic", "Endodoncia"),
            ("crown", "Corona"),
            ("prosthesis", "Prótesis"),
            ("implant", "Implante"),
            ("extraction", "Extracción / Ausente"),
            ("root_fragment", "Resto radicular"),
            ("missing", "Ausente (no erupcionó)"),
        ],
        string="Estado",
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

    _patient_tooth_surface_phase_unique = models.Constraint(
        "unique (patient_id, tooth_id, surface, phase)",
        "Este paciente ya tiene un estado registrado para esa superficie y fase de la pieza.",
    )

    @api.depends("patient_id.name", "tooth_id.fdi_code", "surface", "phase", "state")
    def _compute_display_name(self):
        state_dict = dict(self._fields["state"].selection)
        phase_dict = dict(self._fields["phase"].selection)
        surface_dict = dict(self._fields["surface"].selection)
        for rec in self:
            code = rec.tooth_id.fdi_code or "?"
            surf = surface_dict.get(rec.surface, "?")
            st = state_dict.get(rec.state, "?")
            ph_short = "previsto" if rec.phase == "planned" else "realizado"
            rec.display_name = f"{code} {surf} — {st} ({ph_short})"

    def write(self, vals):
        if any(k in vals for k in ("state", "notes", "phase", "surface")):
            vals["last_updated"] = fields.Datetime.now()
        return super().write(vals)
