# Estado actual del proyecto

Actualizado al **2026-05-15**, commit `c5727d4` (25 commits totales).

## Commits cronológicos

```
8c579da  Slice 0 — scaffold + clinic.specialty jerárquico
1eccc8c  Slice 1 — identidad (refactorizado después en 0a4c682)
c9a8b73  Slice 2 — OS + vías + tarifas + FACO + cobertura
fe9ab0c  Slice 3 — profesionales (hr.employee extended + role + practice)
da64a12  Slice 4 — turnos (FHIR + availability on-the-fly)
1e2129f  Slice 5 — dashboard secretaría
a43bd59  fix — coverage.company_id (remove required from related)
f0202ff  fix — calendar view color attr circular
df20919  Slice 6 — wizard de disponibilidad
9b31182  Slice 7 — valoración tentativa
bdcd173  fix — tz-aware datetimes en get_available_slots
baaac6e  HC auto-sequence + DNI-only validation
d5dd43a  drop end_date/end_reason del paciente
1ffc800  age field computed
0a4c682  REFACTOR identity — drop clinic.contact y clinic.person.contact
1ee9014  fix — external_contact_summary recomputes en cambios de links
2d0e1a5  patient reuse + restrict link picker
9c49bf6  link domain to clinic persons (intermedio)
745b381  DNI search en partner picker (intermedio, deprecated por fca8b29)
fca8b29  DNI lookup autofills + reuses partner (no preguntar al user)
421040f  simplified practitioner form (own view)
7b2ba8a  clean header — readonly labels DNI/matrícula
780132c  hr.employee.write → sync name a work_contact_id
d322151  bidi name sync hr.employee ↔ partner
c5727d4  age consistency: parent older than child
```

## Modelos del proyecto

### En `clinic_core` (16 modelos)
- `clinic.specialty` (jerárquico con `_parent_store`)
- `clinic.patient` (`_inherits res.partner`, per-company)
- `clinic.person.link` (bidi auto con `mirror_id`)
- `clinic.health.insurance` (catálogo OS)
- `clinic.billing.route` (DIRECTO/ASOR/AOSS)
- `clinic.insurance.route` (matriz OS ↔ vía, per-company)
- `clinic.practice` (catálogo FACO con código `CC.SS.NN`)
- `clinic.patient.coverage` (cobertura del paciente)
- `clinic.tariff` (lo que paga la OS)
- `clinic.bond.system` (sistema de bonos tipo IAPOS)
- `clinic.copayment` (copago del paciente)
- `clinic.practice.code.os` (mapeo código FACO → código OS)
- `clinic.practitioner.role` (per-company, patrón FHIR PractitionerRole)
- `clinic.practitioner.practice` (puente prof ↔ práctica)
- `clinic.appointment` (turno, estados FHIR)
- `clinic.dashboard` (TransientModel para dashboard)
- `clinic.appointment.wizard` + `.slot` (wizard de búsqueda)

### Extensiones a modelos Odoo
- `res.partner` — birthdate, gender, is_clinic_person, is_clinic_patient (computed), age (computed), clinic_observations + override name_search/write
- `hr.employee` — is_clinic_practitioner, medical_license, vat (related), specialties, duration override, override create/write para sync con partner, action_view_appointments, action_create_clinic_patient, get_available_slots, get_default_appointment_duration

### En `clinic_dental`
- Scaffold vacío. Solo manifest.

## Demo data cargado

Snapshot SQL al último commit:

```
patients          12   (incl. 8 demo + algunos remanentes de cargas previas)
practitioners      4   (Tenaglia, Soto, Cardozo, +1 test)
appointments      21   (5 hoy en distintos estados, futuros, pasados con noshow/cancelled)
coverages          7   (1 doble Ana IAPOS+Swiss, 2 adherentes Sofía/Lucas)
links              8   (4 originales + 4 mirrors bidi)
practices         28   (FACO Capítulos 1, 2, 3, 5, 7, 8, 9, 10)
tariffs           16   (AVALIAN+AOSS nov-2025 real del PDF)
specialties       16   (Odonto + 8 sub, Cardio + 3 sub, Pedia + 1 sub, Clínica)
health_insurance   6   (PARTICULAR, IAPOS, AVALIAN, OSDE, Swiss, Galeno)
billing_route      3   (DIRECTO, ASOR, AOSS)
```

## Estado funcional V1

✅ **Core operativo completo**: paciente → buscar disponibilidad → agendar turno → confirmar → atender → ver presupuesto.

⚠️ **Features pendientes para V1 completo**:
- Copagos AVALIAN (faltan, solo cargué `amount_paid_by_os`).
- Tarifas IAPOS/OSDE/Swiss/Galeno (no cargadas — están en 0).
- Reportes imprimibles (agenda diaria, recibos).
- Tests automatizados de lógica crítica.
- Tarifario propio del Colegio (FACO con desglose costo_fijo/variable/honorario) — V2.
- Sistema completo de adicionales profesional (3 modelos del doc 05) — V2.

🔮 **V2 declarado** (fuera de scope V1):
- Sync Google Calendar (decisión C diferida).
- Bot WhatsApp + LLM.
- Facturación completa (con `account`, `l10n_ar`).
- Historia clínica detallada.
- Snapshots inmutables de cobro.
- Autocompletar DNI desde fuente externa (RENAPER convenio, AFIP-WSAA o servicio pago).

## Próximos pasos sugeridos

| Opción | Descripción |
|---|---|
| Cargar copagos AVALIAN + tarifas IAPOS/OSDE/Swiss/Galeno | Datos sin código |
| Empezar `clinic_dental` (odontograma) | Módulo dental — odontograma 32 piezas, tratamientos |
| Reportes imprimibles | Agenda diaria, recibo de turno, presupuesto PDF |
| Tests automatizados | Lógica crítica: cascada, get_available_slots, transiciones, overlap |
| UX polish | Probar UI real y refinar lo que aparezca |
