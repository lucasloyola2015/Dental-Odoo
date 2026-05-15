from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_clinic_person = fields.Boolean(
        string="Persona Clínica",
        default=False,
        index=True,
        help="Marca este contacto como una persona física manejada por el módulo de clínica.",
    )
    birthdate = fields.Date(
        string="Fecha de Nacimiento",
        tracking=True,
    )
    gender = fields.Selection(
        selection=[
            ("male", "Masculino"),
            ("female", "Femenino"),
            ("non_binary", "No binario"),
            ("prefer_not_to_say", "Prefiere no decir"),
            ("other", "Otro"),
        ],
        string="Género",
        tracking=True,
    )
    clinic_observations = fields.Text(
        string="Observaciones",
        help="Texto libre con información relevante para la atención. Lo lee el equipo clínico.",
    )
