# Decisiones de modelado (A-O)

Cómo se aterriza el dominio del proyecto en Odoo 19. Cerradas con el usuario. Cambiarlas requiere discusión explícita.

---

## A — Multi-tenancy: `res.company` desde V1
- En V1 hay 1 sola company pero el modelo está armado multi-company.
- Catálogos compartidos (`company_id = False`): obras sociales, FACO, especialidades, tarifarios de referencia, vías de facturación.
- Per-company: pacientes (con `res.partner` compartido), turnos, slots, conversaciones, facturas.

**Why:** beneficio compounde en V2. Facturación nativa filtra por company, migración a SAS limpia, multi-clínica preparada.

---

## B — Identidad: `res.partner` + `clinic.patient` con `_inherits` (refactorizado 2026-05-15)
- `res.partner` extendido con `birthdate`, `gender`, `is_clinic_person`, `is_clinic_patient` (computed), `age` (computed), `clinic_observations`.
- `clinic.patient` con `_inherits = {'res.partner': 'partner_id'}` (per-company). Hereda todos los campos del partner via delegate.
- **Canal de contacto = `res.partner.phone`/`email` nativos** (no más modelo de canal). Flag `clinic.patient.use_external_contact`: si True, esconde phone/email propios y muestra resumen computed con datos de los vínculos `can_be_contacted=True`.
- `clinic.person.link` vínculos humanos con **bidirección automática** (campo `mirror_id`). Tipos simétricos donde aplica + map `INVERSE_TYPE` (parent↔child, etc.). Mirror se crea/edita/elimina automáticamente. Tipos sin distinguir sexo.
- **Flags** del link (is_legal_guardian, can_consent, can_be_contacted) son INDEPENDIENTES en cada lado (semántica: "lo que A puede hacer sobre B").
- Constraint en `clinic.patient`: debe tener phone/email propio O al menos un link con `can_be_contacted=True`.

**Modelos ELIMINADOS** en refactor 2026-05-15: `clinic.contact`, `clinic.person.contact`. Estaban sobre-diseñados.

**Why:** reutilizar `res.partner` da name/vat/email/phone/mail.thread gratis. La separación Persona/Paciente/Vínculo se mantiene; canales se simplifican a fields nativos.

---

## C — Turnos: `clinic.appointment` SoT + `calendar.event` espejo (espejo diferido)
- `clinic.appointment` modelo nuevo con toda la lógica de negocio + estados FHIR-style (`proposed | pending | booked | arrived | fulfilled | cancelled | noshow | waitlist | checked-in | entered-in-error`).
- Vista calendar propia (no se usó `calendar.event` espejo en V1 — diferido a V2 cuando llegue sync Google Calendar).
- Sync a Google Calendar custom unidireccional (V2).

**Why:** módulo `appointment` no existe en Community (es Enterprise). Extender `calendar.event` choca con `recurrence`, no modela estados clínicos ni sobreturnos.

---

## D — Slots on-the-fly con cascada de duración
- **NO se pre-generan slots.** Availability se calcula on-the-fly desde `resource.calendar` (horarios laborales) + `clinic.appointment` existentes.
- Cascada de duración por defecto al crear un turno:
  1. `clinic.practitioner.practice.default_duration_minutes` (override per práctica) →
  2. `hr.employee.default_appointment_duration_minutes` (override del profesional) →
  3. `clinic.specialty.default_appointment_duration_minutes` (de la especialidad principal) →
  4. **30 minutos** (fallback).

**Why:** los 3 SaaS profesionales (Doctolib, Cliniko, SimplePractice) calculan availability on-the-fly. `resource.calendar` ya hace el cómputo. Granularidad flexible por práctica.

---

## E — Sede física: `clinic.location` (resuelto 2026-05-16, ver decisión P)
- ~~En V1 cada `res.company` tiene 1 sede modelada con sus campos de address.~~
- **Reabierto y resuelto**: el caso de uso de Lucas es multi-sede física dentro de UNA misma empresa legal (mismo CUIT). Se modeló `clinic.location` — ver decisión P.

**Why:** El uso real exige distinguir sedes; profesionales con horarios distintos por sede; turnos atados a sede.

---

## F — Especialidad: `clinic.specialty` modelo nuevo (NO `hr.department`)
- Modelo propio simple: `name`, `code`, `default_appointment_duration_minutes`, `active`, `parent_id` (jerárquico con `_parent_store`).
- Se asigna al profesional (`hr.employee.specialty_ids` Many2many + `specialty_main_id` Many2one).
- Separado de `hr.department` (estructura organizacional: Administración, Gerencia, etc.).

**Why:** "Odontología" no es un departamento RRHH; mezclar confunde reportes.

---

## G — Práctica: `clinic.practice` modelo NUEVO simple (NO extender `product.template` en V1)
- Modelo propio con campos FACO (`faco_code` `CC.SS.NN`, capítulo, etc.) + duración por defecto.
- Catálogo compartido (`company_id = False`) porque FACO es nacional.
- En V2 con facturación, se migra a `_inherits = {'product.template': 'product_tmpl_id'}` (aditivo, no destructivo).

**Why:** en V1 no facturamos. Extender `product.template` trae complejidad innecesaria.

---

## H — N° de Historia Clínica auto-generado
- Sequence `clinic.patient.hc` con prefix `HC-%(year)s` y padding 4. Formato: `HC-20260001`.
- Generado en `clinic.patient.create()` cuando el campo está vacío.
- Campo `readonly=True` en la UI.
- Constraint UNIQUE per company como defensa.

**Why:** patrón Odoo idiomático (sale.order, account.move, hr.employee). Audit-friendly: nunca recicla números.

---

## I — Identificación: SOLO DNI (no CUIT)
- `res.partner.vat` se relabel a "DNI" en todas las vistas clínicas.
- Constraint Python en `res.partner` para clinic persons: `vat` debe ser 7-8 dígitos, normalizado (sin puntos/guiones/espacios).

**Why:** en AR, CUIT es para personas jurídicas. Pacientes son personas físicas → DNI.

---

## J — Flujo "DNI-first" en alta de paciente
- Al cargar un paciente nuevo, **el primer dato es el DNI**.
- Onchange en `clinic.patient.vat` hace lookup automático:
  - Si la persona ya es paciente en la company → warning bloqueante "Ya es paciente".
  - Si la persona existe pero no es paciente (médico, titular OS, contacto) → **autocompleta** nombre/birthdate/gender/phone/email silenciosamente.
- `clinic.patient.create()` detecta DNI existente y **reusa el `res.partner`** (no duplica). Drop de los campos delegados en `vals`.
- `res.partner.name_search` override permite buscar por DNI en cualquier picker Many2one(res.partner).

**Why:** sistema piensa, usuario no recuerda. Ver lecciones UX.

---

## K — Lista única de vínculos con bidi automático
- `clinic.person.link.mirror_id` Many2one self apunta al inverso.
- Override de `create/write/unlink` mantiene la pareja sincronizada (semántica invertida + flags independientes).
- Selection sin distinguir sexo: parent en vez de padre/madre, child en vez de hijo/hija, etc.
- En el form de paciente: **una sola lista** (`clinic_link_as_b_ids`) que muestra "X es Y de mí" — el mirror auto-cubre el inverso.
- Constraint `_check_generational_age`: parent/grandparent deben haber nacido antes que child/grandchild.

---

## L — Filtro de vínculos: solo `is_clinic_patient=True`
- `res.partner.is_clinic_patient` (computed stored, depende de `clinic_patient_ids.active`).
- `partner_a_id` y `partner_b_id` de `clinic.person.link` filtran por este flag.
- Implicación: TODO contacto relevante (incluido titular OS no-atendido) debe ser Patient. En el demo, Pedro Méndez se cargó como Patient para satisfacer esto.

---

## M — Sync bidirectional `hr.employee.name` ↔ `res.partner.name` (work_contact_id)
- Odoo nativo NO sincroniza nombre entre employee y su `work_contact_id`. Bug visible.
- Override de `write` en ambos modelos con context flag `_syncing_name` para evitar loops.
- Para `clinic.patient` esto NO se necesita — `_inherits` lo hace gratis (delegación, un solo valor).

---

## N — Form simplificado de profesional (vista propia, no inherit)
- Vista form NUEVA `view_clinic_practitioner_form` para `hr.employee`, usada solo desde "Clínica → Profesionales".
- Solo muestra campos clínicos: DNI, email, teléfono, matrícula, especialidades, duración, buffer. + tabs (roles, prácticas, notas).
- **Evitar `image_1920` con class `oe_avatar`** — en v19 inyecta auto work_email/work_phone/mobile_phone/job_title como inputs editables.
- Cabecera: name editable (h1) + subtítulo readonly con matrícula y DNI como labels.
- Forzar la vista via `view_ids` en la action (no `view_mode` solo).

---

## O — Paciente: campos simplificados al máximo
- Sin `end_date` ni `end_reason` (archivar con `active=False`).
- `start_date` readonly, default `context_today`, mostrar como etiqueta gris bajo el nombre.
- `age` computed (non-stored) desde `birthdate`.

---

## P — Multi-sede física: `clinic.location` (2026-05-16)

Caso de uso: una sola empresa legal (`res.company`) con N sucursales físicas. Un profesional puede trabajar en varias sedes con horarios distintos. Esto **reemplaza la decisión E original**.

### Modelo
- **`clinic.location`** (modelo nuevo): `name`, `code`, `company_id` (req), `partner_id` (auto-create al guardar — guarda address/phone/email), `billing_route_id` (req — asociación regional), `sequence`, `active`, `notes`.
- Patrón Odoo: `stock.warehouse`/`pos.config` usan `partner_id` para address. Patrón FHIR: `Organization 1..* Location`.
- UNIQUE `(code, company_id)`.

### Asociaciones regionales (AOSS, ASOR, etc.)
- **Ya estaban modeladas como `clinic.billing.route`**. La novedad es el **vínculo sede → asociación**: `location.billing_route_id` required.
- Las tarifas (`clinic.tariff`) siguen colgando de `(OS, billing_route, practice)` per-company. Llegan a una sede via `location → billing_route → tariffs`. **No se agregó `location_id` a `tariff`** — pricing se resuelve por transitividad.

### Modelos refactorizados (`company_id` → `location_id`)
| Modelo | Cambio |
|---|---|
| `clinic.practitioner.role` | `location_id` required. UNIQUE pasa a `(employee, location)`. `company_id` queda como `related="location_id.company_id"` stored para compat. |
| `clinic.practitioner.practice` | `location_id` required. UNIQUE pasa a `(employee, practice, location)`. Precio particular puede variar por sede. |
| `clinic.appointment` | `location_id` required. Overlap check ahora es por `(practitioner, location)` — no cross-location. Default `billing_route_id` = `location.billing_route_id`. |
| `hr.employee.get_resource_calendar_for_company(company)` | Renombrado a `get_resource_calendar_for_location(location)`. |
| `hr.employee.get_available_slots(...)` | Parámetro `company` → `location`. Filtro de busy slots por `location_id`. |

### Modelos que NO cambian
- `clinic.patient`, `clinic.patient.coverage`: per-company (el paciente es de la organización entera, puede atenderse en cualquier sede).
- `clinic.tariff`, `clinic.copayment`, `clinic.bond.system`, `clinic.billing.route`, `clinic.health.insurance`, `clinic.insurance.route`, `clinic.practice`, `clinic.specialty`, `clinic.practice.code.os`: catálogos administrativos/legales, per-company o compartidos.

### Demo data
Cargado por `scripts/load_demo_data.py`: 2 sedes — **ROL** (Roldán Centro, AOSS) y **FUN** (Funes, ASOR). Dra. Tenaglia atiende en ambas con horarios distintos (ROL 9-13/14-18, FUN 10-13/15-19). Dr. Soto solo en ROL. Dra. Cardozo solo en FUN.

**Why:** matchea el dominio real (misma empresa, múltiples consultorios), no abusa `res.company` (que es entidad contable). Asociaciones regionales por sede sale gratis del `billing_route_id` ya modelado. Tarifas no se duplican.

---

## Cómo aplicar estas decisiones

- Antes de proponer modelos nuevos, releer estas decisiones.
- Si una decisión nueva del usuario contradice una de estas → parar y discutir explícitamente.
- Decisiones nuevas → agregar entrada con letra siguiente (P, Q, ...) en este archivo.
