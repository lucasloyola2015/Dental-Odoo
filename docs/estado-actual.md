# Estado actual del proyecto

Actualizado al **2026-05-17**, commit `99e672c` (38 commits totales).

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
9251bcd  docs: CLAUDE.md + docs/ folder versionados en git
97ad647  multi-sede + schedules + routing_mode refactor (decisión P)
e731098  demo loader reescrito para multi-sede (ROL + FUN, extras, leaves)
9aa9245  fix — slots = 0 cuando practitioner no tiene rol en la sede
023d005  smart buttons "Profesionales" y "Turnos" en clinic.location
7146116  global appointments calendar filtrable por sede
64a1472  notifications — 4 mail templates + 2 crons + WhatsApp preview
2061683  docs: refresh estado-actual a 64a1472
2ca3055  refactor — PARTICULAR singleton + tarifario Colegio + % por sede (decisión Q)
a1d37ff  data — catálogo Colegio completo (193 prácticas + 162 tarifas reales abril 2026)
89146db  refactor — agrupar Configuración en 3 sub-carpetas (Estructura, OS, Asignación)
3b197fb  data — AVALIAN completa (44 tarifas + 44 copagos + 5 overrides de código)
99e672c  smart buttons en form de Obra Social (tarifas/copagos/bonos/códigos/vías)
```

## Modelos del proyecto

### Propios en `clinic_core` (18 modelos)
- `clinic.specialty` (jerárquico con `_parent_store`)
- `clinic.patient` (`_inherits res.partner`, per-company)
- `clinic.person.link` (bidi auto con `mirror_id`)
- `clinic.health.insurance` (catálogo OS). **PARTICULAR es singleton** identificado por xml_id `clinic_core.health_insurance_particular` (decisión Q).
- `clinic.billing.route` (DIRECTO/ASOR/AOSS/PARTICULAR)
- `clinic.insurance.route` (matriz OS ↔ vía, per-company)
- `clinic.practice` (catálogo FACO con código `CC.SS.NN`)
- `clinic.patient.coverage` (cobertura del paciente)
- `clinic.tariff` (lo que paga la OS — incluye OS=PARTICULAR para precios del Colegio)
- `clinic.bond.system` (sistema de bonos tipo IAPOS)
- `clinic.copayment` (copago del paciente — lo que paga además de lo que cubre la OS)
- `clinic.practice.code.os` (mapeo código FACO → código OS, sólo overrides)
- `clinic.location` (sede física, decisión P)
- `clinic.practitioner.role` (per-company + per-location, patrón FHIR PractitionerRole). Tiene `particular_percentage` (% sobre Colegio cuando atiende particular).
- `clinic.practitioner.practice` (puente prof ↔ práctica, per-location). Sin `price_particular` (se calcula via tarifa Colegio × % del role).
- `clinic.schedule.extra_day` (días extra one-off de atención)
- `clinic.appointment` (turno, estados FHIR, location_id requerido). El compute de presupuesto particular lee tarifa PARTICULAR × role.particular_percentage / 100.
- `clinic.dashboard` (TransientModel para dashboard)

Wizards: `clinic.appointment.wizard` + `clinic.appointment.wizard.slot`.

### Extensiones a modelos Odoo
- `res.partner` — birthdate, gender, is_clinic_person, is_clinic_patient (computed), age (computed), clinic_observations + override name_search/write
- `hr.employee` — is_clinic_practitioner, medical_license, vat (related), specialties, duration override, override create/write para sync con partner, `get_resource_calendar_for_location` (strict, sin fallback al calendario HR nativo), `get_available_slots` per-location
- `resource.calendar` — override `_work_intervals_batch` para fusionar `clinic.schedule.extra_day` activos como intervalos de trabajo; campo computado `routine_grid_html` (heatmap semanal Mon-Sun × 06:00-22:00 en slots de 30 min)
- `resource.calendar.attendance` / `.leaves` — campo `active` (soft-toggle); `ir.rule` para usuarios `clinic`

### En `clinic_dental`
- Scaffold vacío. Solo manifest. **Próximo bloque grande** (ver "Próximos pasos").

## Decisión Q — PARTICULAR como OS singleton (commit `2ca3055`)

Revisión de decisiones cerradas en doc 05 de ClinicBot (líneas 1466 y 1475). El modelo final:

- **PARTICULAR es una OS** identificada por xml_id estable (`clinic_core.health_insurance_particular`); ya no hay flag `is_particular`.
- **Tarifario del Colegio** vive en `clinic.tariff` con OS=PARTICULAR, route=PARTICULAR. Una sola fila por práctica con `amount_paid_by_os` = precio total Colegio. Versionado por `valid_from`.
- **% del profesional** vive en `clinic.practitioner.role.particular_percentage` (Float, default 100). Por sede.
- **Cálculo del precio particular**: `tarifa(PARTICULAR, práctica, vigente).amount_paid_by_os × role.particular_percentage / 100`.
- **Gastos fijos clínica**: diferidos a iteration futura (en V1 todo va dentro del precio Colegio × % profesional).

## Smart buttons en form de OS (commit `99e672c`)

`clinic.health.insurance` form muestra 5 stat buttons que llevan a sus relacionados filtrados por OS:
- Tarifas, Copagos, Bonos, Códigos (mapeos a códigos OS distintos del Colegio), Vías (que la aceptan).

## Reorganización del menú Configuración (commit `89146db`)

Pasó de 12 items planos a 3 sub-carpetas:
- **Estructura**: Sucursales, Especialidades, Catálogo del Colegio (FACO).
- **Obras sociales**: Listado de OS, Vías de facturación, Vías × OS (matriz), Tarifas, Bonos, Copagos, Códigos por OS.
- **Asignación profesional**: Roles por sede, Prácticas por profesional.

## Demo data cargado

```
locations          2     (ROL = Roldan Centro/AOSS, FUN = Funes/ASOR)
patients          12     (8 demo + remanentes)
practitioners      4     (Tenaglia, Soto, Cardozo, +1 test)
roles              4     (Tenaglia ROL+FUN, Soto ROL, Cardozo FUN — con particular_percentage)
appointments      21     (16 ROL + 5 FUN)
coverages          7
links              8     (4 originales + 4 mirrors bidi)
specialties       16
health_insurance   6     (PARTICULAR, IAPOS, AVALIAN, OSDE, Swiss, Galeno)
billing_route      4     (DIRECTO, ASOR, AOSS, PARTICULAR)
extras_days       ~6
leaves            ~4
```

## Catálogos de referencia cargados

```
clinic.practice         193   (catálogo Colegio Odon. Santa Fe 2da Circ. completo, 12 capítulos)
clinic.tariff PARTICULAR 162  (precios reales Colegio abril 2026)
clinic.tariff AVALIAN     44  (grilla AVALIAN vigencia 11/2025 vía AOSS)
clinic.copayment AVALIAN  44  ("a cargo del socio" según PDF AVALIAN)
clinic.practice.code.os    5  (5 overrides AVALIAN: cefalometría + 4 tomografías cone-beam)
clinic.bond.system IAPOS   1  (valor placeholder; PDF IAPOS es imagen escaneada)
```

## Estado funcional V1

✅ **Core operativo completo**: paciente → buscar disponibilidad → agendar → confirmar → atender → ver presupuesto.

✅ **Multi-sede operativo**: profesionales con roles per-sede, precios per-sede, calendario per-sede, turnos per-sede, calendar global filtrable.

✅ **Editor de horarios**: rutina, días extra, períodos excluidos, vista semanal.

✅ **Notifications armadas**: 4 templates + 2 crons + toggles por sede + WhatsApp preview. **Pendiente: verificar con SMTP real**.

✅ **Catálogo del Colegio completo y tarifas PARTICULAR reales**.

✅ **AVALIAN completa**: tarifas + copagos + códigos override.

✅ **UX**: menú Configuración reorganizado en 3 sub-carpetas + smart buttons en form de OS.

⚠️ **Features pendientes para V1 completo**:
- Validar notifications end-to-end (SMTP + outbox + cron real).
- Tarifas IAPOS (PDF es imagen, requiere OCR o transcripción manual).
- Tarifas OSDE/Swiss/Galeno (sin PDF cargado todavía).
- Reportes imprimibles (agenda diaria, recibo de turno, presupuesto PDF).
- Tests automatizados de lógica crítica.

🔮 **V2 declarado** (fuera de scope V1):
- Sync Google Calendar (decisión C diferida).
- Bot WhatsApp + LLM (mientras tanto, WhatsApp preview en el form).
- Facturación completa (con `account`, `l10n_ar`).
- Historia clínica detallada.
- Snapshots inmutables de cobro.
- Autocompletar DNI desde fuente externa (RENAPER convenio, AFIP-WSAA o servicio pago).

## Próximos pasos sugeridos

| Opción | Descripción |
|---|---|
| **clinic_dental** — odontograma + tratamientos | Próximo módulo grande. Modelo de piezas dentarias (32 permanentes + 20 temporales), estado por pieza, plan de tratamiento, link a `clinic.appointment.practice_id`. |
| Validar notifications end-to-end | Configurar SMTP, mandar test, verificar cron 24h. Cierra la feature de email. |
| Cargar IAPOS (OCR o manual) | El PDF tiene la grilla como imagen. Necesita OCR o transcripción. |
| Cargar OSDE/Swiss/Galeno | Cuando tengamos los PDFs/grillas. |
| Reportes imprimibles | Agenda diaria, recibo de turno, presupuesto PDF. |
| Tests automatizados | Lógica crítica: cascada, get_available_slots, transiciones, overlap, cálculo de presupuesto (particular + OS). |
| UX polish | Smart buttons en otros forms (Sede ya tiene; Práctica podría tener "X tarifas cargadas"). |
