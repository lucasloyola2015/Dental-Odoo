{
    "name": "Clinic Core",
    "version": "19.0.1.0.0",
    "category": "Healthcare",
    "summary": "Base genérica para clínica médica multi-especialidad",
    "description": """
Clinic Core
===========
Modelo base para clínica médica multi-especialidad.

Provee:
- Extensión de res.partner para personas clínicas (fecha de nacimiento, género).
- Catálogo de especialidades clínicas.
- Grupos de seguridad: Secretaría, Administración.

Las extensiones por especialidad (clinic_dental, clinic_cardio, etc.) se apoyan
en este módulo.
""",
    "author": "Lucas Loyola",
    "website": "",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "contacts",
        "hr",
        "product",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/menu_views.xml",
        "views/res_partner_views.xml",
        "views/clinic_specialty_views.xml",
        "data/clinic_specialty_data.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
