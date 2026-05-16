# Estado actual del proyecto

Actualizado al **2026-05-16**, commit `64a1472` (32 commits totales).

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
```

## Modelos del proyecto

### Propios en `clinic_core` (18 modelos)
- `clinic.specialty` (jerárquico con `_parent_store`)
- `clinic.patient` (`_inherits res.partner`, per-company)
- `clinic.person.link` (bidi auto con `mirror_id`)
- `clinic.health.insurance` (catálogo OS)
- `clinic.billing.route` (DIRECTO/ASOR/AOSS/PARTICULAR)
- `clinic.insurance.route` (matriz OS ↔ vía, per-company)
- `clinic.practice` (catálogo FACO con código `CC.SS.NN`)
- `clinic.patient.coverage` (cobertura del paciente)
- `clinic.tariff` (lo que paga la OS)
- `clinic.bond.system` (sistema de bonos tipo IAPOS)
- `clinic.copayment` (copago del paciente)
- `clinic.practice.code.os` (mapeo código FACO → código OS)
- `clinic.location` (**nuevo**, decisión P — sede física dentro de la company)
- `clinic.practitioner.role` (per-company + per-location, patrón FHIR PractitionerRole)
- `clinic.practitioner.practice` (puente prof ↔ práctica, ahora también per-location)
- `clinic.schedule.extra_day` (**nuevo** — días extra one-off de atención)
- `clinic.appointment` (turno, estados FHIR, ahora con location_id requerido)
- `clinic.dashboard` (TransientModel para dashboard)

Wizards: `clinic.appointment.wizard` + `clinic.appointment.wizard.slot`.

### Extensiones a modelos Odoo
- `res.partner` — birthdate, gender, is_clinic_person, is_clinic_patient (computed), age (computed), clinic_observations + override name_search/write
- `hr.employee` — is_clinic_practitioner, medical_license, vat (related), specialties, duration override, override create/write para sync con partner, `get_resource_calendar_for_location` (strict, sin fallback al calendario HR nativo), `get_available_slots` per-location
- `resource.calendar` — override `_work_intervals_batch` para fusionar `clinic.schedule.extra_day` activos como intervalos de trabajo; campo computado `routine_grid_html` (heatmap semanal Mon-Sun × 06:00-22:00 en slots de 30 min)
- `resource.calendar.attendance` — campo `active` (soft-toggle por línea de rutina, leído por el default `active_test` de Odoo)
- `resource.calendar.leaves` — campo `active` análogo; `ir.rule` para usuarios `clinic` (la rule nativa restringía leaves al resource propio)

### En `clinic_dental`
- Scaffold vacío. Solo manifest.

## Decisión P — multi-sede (commit `97ad647`)

Cerró la decisión E (diferida) modelando una **sede física** como `clinic.location` dentro de una sola `res.company`. La motivación: un médico que alquila un consultorio en 2 lugares no es 2 companies — es 1 persona con 2 sedes, con disponibilidad, vías de facturación y precios potencialmente distintos por sede.

Implicancias propagadas:
- `clinic.practitioner.role`, `clinic.practitioner.practice` y `clinic.appointment` llevan `location_id` requerido. `company_id` sigue siendo `related` stored para compatibilidad multi-company nativa.
- Precios `price_particular` por (profesional, práctica, **sede**) — un mismo profesional puede cobrar distinto en cada sede.
- `routing_mode` se convirtió en `assigned_route_id` (Many2one a `clinic.billing.route`, dominio dinámico = `location.billing_route_id` + PARTICULAR). El `routing_mode` selection sigue existiendo como computed store para no romper código aguas abajo.
- Overlap de turnos chequea por `(practitioner, location)`.
- Address de la sede vía `res.partner` auto-creado en el create de `clinic.location` (patrón de `stock.warehouse`).

## Editor de horarios (commit `97ad647`)

Botón `📅 Editar horarios` en cada fila de la tab "Sedes y horarios" del profesional → abre un modal con `resource.calendar` y 3 tabs:
- **Rutina**: grilla nativa de `resource.calendar.attendance` con toggle `active` por línea.
- **Días extra**: lista de `clinic.schedule.extra_day` (date + hour_from/hour_to).
- **Períodos excluidos**: lista de `resource.calendar.leaves` con `active`.

Tab adicional "Vista semanal" con `routine_grid_html` — heatmap read-only para inspección rápida.

## Notifications (commit `64a1472`)

4 mail templates en español rioplatense (confirmación, recordatorio 24h, recordatorio 2h, cancelación) + 2 crons (24h diario, 2h cada 30 min). Cada sede tiene 4 toggles boolean (`send_*_email`) para prender/apagar cada tipo de notificación independientemente.

`clinic.appointment` trackea 4 flags `*_sent` para evitar duplicados y expone `whatsapp_message_preview` (texto pre-armado para copy/paste mientras no haya WhatsApp Cloud API). Confirmación y cancelación se envían automáticamente desde las transiciones de estado existentes; también hay 2 botones manuales en el form.

⚠️ **No probado end-to-end todavía** — requiere SMTP configurado en Odoo. Las plantillas y crons están armados pero la salida real no se verificó.

## Demo data cargado (post-rewrite multi-sede)

```
locations          2   (ROL = Roldan Centro/AOSS, FUN = Funes/ASOR)
patients          12   (8 demo + remanentes de cargas previas)
practitioners      4   (Tenaglia, Soto, Cardozo, +1 test)
roles              5   (Tenaglia ROL+FUN, Soto ROL, Cardozo FUN, +1 test)
appointments      21   (16 ROL + 5 FUN, mix de estados)
coverages          7   (1 doble Ana IAPOS+Swiss, 2 adherentes Sofía/Lucas)
links              8   (4 originales + 4 mirrors bidi)
practices         28   (FACO Capítulos 1, 2, 3, 5, 7, 8, 9, 10)
tariffs           16   (AVALIAN+AOSS nov-2025 real del PDF)
specialties       16   (Odonto + 8 sub, Cardio + 3 sub, Pedia + 1 sub, Clínica)
health_insurance   6   (PARTICULAR, IAPOS, AVALIAN, OSDE, Swiss, Galeno)
billing_route      4   (DIRECTO, ASOR, AOSS, PARTICULAR)
extras_days        ~6  (sábados extra + horarios ampliados)
leaves             ~4  (vacaciones, congreso, cumpleaños)
```

Calendario `resource.calendar` ahora es **uno por (practitioner, location)** — antes 2 profesionales en la misma sede compartían calendario, latent bug corregido en `e731098`.

## Estado funcional V1

✅ **Core operativo completo**: paciente → buscar disponibilidad → agendar → confirmar → atender → ver presupuesto.

✅ **Multi-sede operativo**: profesionales con roles per-sede, precios per-sede, calendario per-sede, turnos per-sede, calendar global filtrable.

✅ **Editor de horarios**: rutina, días extra, períodos excluidos, vista semanal.

✅ **Notifications armadas**: 4 templates + 2 crons + toggles por sede + WhatsApp preview. **Pendiente: verificar con SMTP real**.

⚠️ **Features pendientes para V1 completo**:
- Validar notifications end-to-end (SMTP + outbox + cron real).
- Copagos AVALIAN (faltan, solo cargué `amount_paid_by_os`).
- Tarifas IAPOS/OSDE/Swiss/Galeno (no cargadas — están en 0).
- Reportes imprimibles (agenda diaria, recibos).
- Tests automatizados de lógica crítica.
- Tarifario propio del Colegio (FACO con desglose costo_fijo/variable/honorario) — V2.
- Sistema completo de adicionales profesional (3 modelos del doc 05) — V2.

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
| Validar notifications end-to-end | Configurar SMTP, mandar test, verificar cron 24h. Cierra la feature de hoy. |
| Cargar copagos AVALIAN + tarifas IAPOS/OSDE/Swiss/Galeno | Datos sin código. |
| Empezar `clinic_dental` (odontograma) | Módulo dental — odontograma 32 piezas, tratamientos. |
| Reportes imprimibles | Agenda diaria, recibo de turno, presupuesto PDF. |
| Tests automatizados | Lógica crítica: cascada, get_available_slots, transiciones, overlap, notifications. |
| UX polish | Probar UI real (especialmente editor de horarios) y refinar. |
