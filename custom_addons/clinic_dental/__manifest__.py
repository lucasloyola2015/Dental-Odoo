{
    'name': 'Clinic Dental',
    'version': '19.0.1.0.0',
    'category': 'Healthcare',
    'summary': 'Extension dental sobre clinic_core',
    'description': """
Extension dental sobre clinic_core.

Incluye:
- Odontograma (vista interactiva 32 piezas)
- Tratamientos dentales (extiende Practica)
- Presupuestos odontologicos
- Catalogo FACO / Colegio Odontologos SF (codigos CC.SS.NN)
""",
    'author': 'Lucas Loyola',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'clinic_core',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/clinic_dental_tooth_views.xml',
        'views/clinic_dental_tooth_state_views.xml',
        'views/clinic_patient_views.xml',
        'views/clinic_appointment_views.xml',
        'data/clinic_dental_tooth_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'clinic_dental/static/src/components/odontogram/odontogram.js',
            'clinic_dental/static/src/components/odontogram/odontogram.xml',
            'clinic_dental/static/src/components/odontogram/odontogram.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
