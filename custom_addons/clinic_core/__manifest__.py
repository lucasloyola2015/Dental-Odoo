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
        "views/clinic_patient_views.xml",
        "views/clinic_contact_views.xml",
        "views/clinic_health_insurance_views.xml",
        "views/clinic_billing_route_views.xml",
        "views/clinic_insurance_route_views.xml",
        "views/clinic_practice_views.xml",
        "views/clinic_tariff_views.xml",
        "data/clinic_specialty_data.xml",
        "data/clinic_billing_route_data.xml",
        "data/clinic_health_insurance_data.xml",
        "data/clinic_insurance_route_data.xml",
        "data/clinic_practice_data.xml",
        "data/clinic_tariff_avalian_data.xml",
        "data/clinic_bond_iapos_data.xml",
        "data/clinic_practice_code_os_data.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
