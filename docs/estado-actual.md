# Estado actual del proyecto

Actualizado al **2026-05-17**, commit `711f128` (47 commits totales).

## Commits cronológicos

```
8c579da..c5727d4   25 commits iniciales — slices 0-7 + refactor identidad + DNI lookup +
                                          practitioner form + name sync + age consistency
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
1c92a97  docs: refresh estado-actual a 99e672c
bb9ddac  clinic_dental V1 — catálogo FDI (52 piezas) + tooth_state + appointment link
dc3708d  clinic_dental iter A — surface + phase en tooth state
3cd5c2a  clinic_dental iter B — OWL widget SVG odontograma (read-only)
5f5aaa6  clinic_dental iter C — click en superficie abre popover de edición
6a5a221  fix — SVG re-renderiza después de save desde popover
bec6c54  fix — drop badge widget en phase para que sea editable inline
f611179  fix — SVG sincroniza con edits de la tabla via useEffect
711f128  fix — load tooth_fdi_code en list + parsing robusto de Many2one
```

## Módulos del proyecto

### `clinic_core` (18 modelos propios)
Core operativo: pacientes, turnos, profesionales, sedes, obras sociales, prácticas FACO, tarifas, copagos, bonos, mapeo de códigos por OS. Ver lista completa de modelos abajo.

### `clinic_dental` (3 modelos propios + extensiones)
Extensión odontológica. **Operativo desde 2026-05-17** con:
- **Catálogo FDI** de 52 piezas (32 permanentes + 20 temporales).
- **Estado por superficie** del paciente: cada pieza tiene 5 caras (oclusal, mesial, distal, vestibular, lingual) × 2 fases (planned/realized) × 9 estados clínicos.
- **Widget SVG interactivo** (OWL component) en la pestaña Odontograma del form de paciente: dibuja el odontograma estándar con caras clickeables, pinta rojo lo previsto/observado y azul lo realizado. Click en una superficie abre popover de edición.
- **Tabla editable** debajo del SVG sincronizada bidireccionalmente.
- **Link con `clinic.appointment`** via M2M `tooth_ids`.

### Catálogos de referencia cargados

```
clinic.practice          193   (catálogo Colegio Odon. Santa Fe 2da Circ. abril 2026)
clinic.dental.tooth       52   (catálogo FDI: 32 permanentes + 20 temporales)
clinic.tariff PARTICULAR 162   (precios reales Colegio abril 2026, vía PARTICULAR)
clinic.tariff AVALIAN     44   (grilla AVALIAN vigencia 11/2025 vía AOSS)
clinic.copayment AVALIAN  44   ("a cargo del socio" según PDF AVALIAN)
clinic.practice.code.os    5   (overrides AVALIAN: cefalometría + 4 tomografías)
clinic.bond.system IAPOS   1   (valor placeholder; PDF IAPOS es imagen escaneada)
```

## Modelos del proyecto

### Propios en `clinic_core`
`clinic.specialty`, `clinic.patient` (`_inherits res.partner`), `clinic.person.link`, `clinic.health.insurance` (PARTICULAR es singleton xml_id), `clinic.billing.route`, `clinic.insurance.route`, `clinic.practice`, `clinic.patient.coverage`, `clinic.tariff`, `clinic.bond.system`, `clinic.copayment`, `clinic.practice.code.os`, `clinic.location`, `clinic.practitioner.role` (con `particular_percentage`), `clinic.practitioner.practice`, `clinic.schedule.extra_day`, `clinic.appointment`, `clinic.dashboard`. Plus wizards `clinic.appointment.wizard` + `.slot`.

### Propios en `clinic_dental`
- `clinic.dental.tooth` — catálogo FDI (52 piezas).
- `clinic.dental.tooth.state` — estado por (paciente, pieza, superficie, fase). Unique (patient_id, tooth_id, surface, phase). Estados: `caries / restoration / endodontic / crown / prosthesis / implant / extraction / root_fragment / missing`. Fases: `planned` (rojo, observado/previsto) / `realized` (azul, realizado/existente).
- Extensiones: `clinic.patient.dental_tooth_state_ids` (O2m), `clinic.appointment.tooth_ids` (M2M).

### Extensiones a modelos Odoo
- `res.partner`, `hr.employee`, `resource.calendar` / `.attendance` / `.leaves` (ver doc anterior).

## Decisiones cerradas hasta hoy

- **A-O**: ver `decisiones-modelo.md`.
- **P**: multi-sede (`clinic.location`) con `billing_route` y `routing_mode`/`assigned_route_id` per role.
- **Q**: PARTICULAR como OS singleton (xml_id estable) + tarifario Colegio + `particular_percentage` por (profesional, sede). Cálculo: `tarifa(PARTICULAR, práctica, vigente).amount_paid_by_os × role.particular_percentage / 100`.
- **Odontograma V1**: por superficie (5 por diente) + fases planned/realized. UI: SVG OWL con click-to-edit via popover. Iteraciones A-C completadas.

## Componente OWL `OdontogramField`

Widget custom registrado como `widget="odontogram"` para One2many.

**Archivos**:
- `clinic_dental/static/src/components/odontogram/odontogram.js` (~250 líneas)
- `odontogram.xml` (template del SVG)
- `odontogram.scss` (estilos)
- `odontogram_popover.js` + `odontogram_popover.xml` (popover de edición)

**Sincronización (críticamente importante)**:
- El widget mantiene un `useState({rows: []})` interno como única fuente de verdad para el render.
- Un `useEffect` vigila un fingerprint string del O2m del padre y mirror-ea cambios al localState. Esto captura tanto:
  - edits inline en la tabla editable de abajo (cambios in-memory del O2m).
  - reloads via `record.load()` que dispara el popover después de un ORM directo.
- Función `_extractToothId(value)` robusta contra las distintas formas que devuelve Odoo 19 para Many2one (array, objeto con `resId`, número raw).

**Limitaciones conocidas**:
- Símbolos visuales del estándar (X para extracción/ausente, Π para prótesis) todavía no se dibujan: hoy todo se pinta con color sólido.
- La extracción/ausencia afecta solo la superficie clickeada, no el diente entero como sería lo ideal.
- Si el paciente está en draft (resId vacío), click-to-edit desde el SVG es no-op. La tabla editable abajo es el fallback.

## Demo data cargado

```
locations          2   (ROL = Roldan Centro/AOSS, FUN = Funes/ASOR)
patients          12
practitioners      4   (Tenaglia, Soto, Cardozo, +1 test)
roles              4   (Tenaglia ROL+FUN, Soto ROL, Cardozo FUN — con particular_percentage)
appointments      21   (16 ROL + 5 FUN)
coverages          7
links              8
specialties       16
health_insurance   6   (PARTICULAR, IAPOS, AVALIAN, OSDE, Swiss, Galeno)
billing_route      4
extras_days       ~6
leaves            ~4
clinic_dental_tooth_state  0  (sin demo data dental por ahora)
```

## Estado funcional V1

✅ **Core operativo completo**: paciente → buscar disponibilidad → agendar → confirmar → atender → ver presupuesto.

✅ **Multi-sede operativo**.

✅ **Editor de horarios** (rutina + extras + leaves + vista semanal).

✅ **Catálogo del Colegio y tarifas PARTICULAR reales abril 2026**.

✅ **AVALIAN completa**: tarifas + copagos + códigos override.

✅ **UX**: menú Configuración reorganizado + smart buttons en form de OS.

✅ **Odontograma operativo**: catálogo FDI + estado por superficie/fase + SVG interactivo + tabla editable + sync bidireccional.

⚠️ **Notifications armadas**: 4 templates + 2 crons + toggles por sede + WhatsApp preview. **Pendiente: verificar con SMTP real**.

⚠️ **Features pendientes para V1 completo**:
- Validar notifications end-to-end (SMTP + outbox + cron real).
- Tarifas IAPOS (PDF es imagen, requiere OCR o transcripción manual).
- Tarifas OSDE/Swiss/Galeno (sin PDF cargado todavía).
- Reportes imprimibles (agenda diaria, recibo de turno, presupuesto PDF).
- Tests automatizados de lógica crítica.
- Símbolos visuales del odontograma (X, Π) además del color.
- Demo data dental (cargar un odontograma de muestra para Pedro Mendez).

🔮 **V2 declarado** (fuera de scope V1):
- Sync Google Calendar (decisión C diferida).
- Bot WhatsApp + LLM.
- Facturación completa (con `account`, `l10n_ar`).
- Historia clínica detallada y plan de tratamiento agregado (presupuesto desde odontograma).
- Snapshots inmutables de cobro.
- Autocompletar DNI desde fuente externa.
- Granularidad superficie evolucionada (más detalle por cara, ej. mesial-oclusal-distal compuesta).

## Próximos pasos sugeridos

| Opción | Descripción |
|---|---|
| Validar notifications end-to-end | Configurar SMTP, mandar test, verificar cron 24h. |
| Símbolos visuales en odontograma | X para extracción/ausente, Π para prótesis. Pulido visual del estándar. |
| Smart button "Odontograma" en form de paciente | Conteo de piezas con estado, abre la pestaña directo. |
| Demo data dental | Cargar odontograma de muestra para 1-2 pacientes demo. |
| Cargar IAPOS (OCR o manual) | PDF es imagen — requiere OCR (pytesseract) o transcripción. |
| Cargar OSDE/Swiss/Galeno | Cuando tengamos los PDFs/grillas. |
| Reportes imprimibles | Agenda diaria, recibo de turno, presupuesto PDF. |
| Tests automatizados | Lógica crítica: cascada, get_available_slots, transiciones, overlap, cálculo de presupuesto (particular + OS). |
