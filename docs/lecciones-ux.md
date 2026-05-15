# Lecciones de UX

Patrones que el usuario valora. Aplicar de oficio, sin esperar a que los pida.

## 1. El sistema piensa, el usuario no recuerda

**Regla:** Cuando hay info que el sistema puede deducir o buscar, **NO** preguntar al usuario.

**Ejemplo concreto (2026-05-15):** Yo había puesto un warning *"esta persona ya existe — cancelá y seleccioná en el campo Persona"*. El usuario respondió: *"¿vos te pensás que tengo memoria para recordar 4000 contactos? Vos te tenés que dar cuenta solo, no me debes preguntar."*

**Cómo aplicar:**
- Si el DNI coincide con un partner existente → autocompletar datos. No preguntar.
- Si la persona ya es paciente en la company → avisar con un warning bloqueante.
- Si la persona existe pero no es paciente → autocompletar y al guardar reusar el partner (no duplicar).

## 2. Formularios mínimos

**Regla:** En cualquier form, mostrar SOLO los campos relevantes para el flujo. No los 50 campos nativos de Odoo.

**Ejemplo concreto:** El usuario al ver el form nativo de `hr.employee` para crear un profesional: *"me abruma los millones de campos. Necesito un mes para completar el formulario. Dejá solo los fundamentales."*

**Cómo aplicar:**
- Para flujos clínicos, **crear vistas form propias** (no `_inherit`) que tengan solo los campos necesarios.
- Forzar la vista custom desde la `act_window` con `view_ids` explícito.
- El form nativo queda para usuarios con permiso técnico (HR admin, dev).

## 3. La cabecera son etiquetas, no inputs

**Regla:** En el área del título/header del form, los datos secundarios son **labels readonly**, no inputs. Solo el campo "principal" (`name`) es editable arriba.

**Ejemplo concreto:** El usuario vio que el form del profesional ponía email, teléfono, etc. como inputs editables debajo del nombre: *"los datos de la cabecera no deben ser editables, deben ser etiquetas cuanto mucho."*

**Cómo aplicar:**
- `<h1>` con el nombre editable.
- `<h3 class="text-muted">` con readonly labels (matrícula, DNI, etc.).
- Edición de esos campos pasa en grupos del cuerpo, NO en el header.
- **Evitar `image_1920` con clase `oe_avatar`** — en v19 inyecta automáticamente work_email/work_phone/mobile_phone/job_title como campos visibles al lado.

## 4. Datos coherentes implícitos

**Regla:** Si dos modelos representan la misma persona (paciente / profesional / contacto), los datos deben sincronizarse automáticamente. El usuario NO debe editar el mismo dato en dos lados.

**Ejemplo concreto:** El usuario notó que editar el nombre del profesional no actualizaba el contacto, y viceversa: *"Si edito el contacto, no se actualizan los pacientes ni los profesionales. ¿Un paciente no extiende de contacto? ¿Por qué no se actualizan de manera bidireccional?"*

**Cómo aplicar:**
- Para `clinic.patient` ↔ `res.partner` con `_inherits`: Odoo lo hace nativo (delegación, un solo valor).
- Para `hr.employee` ↔ `res.partner` (sin `_inherits`, `work_contact_id` Many2one): hay que hacer **override de write en ambos lados** con flag de context (`_syncing_name`) para evitar loops.

## 5. No reinventar lo que el modelo de datos ya hace

**Regla:** Si necesitás "deshabilitar" un paciente, NO crees un campo `is_archived` ni `end_date`. Usá `active=False` (patrón Odoo nativo). El chatter ya trackea cuándo se archivó.

**Ejemplo concreto:** El usuario sobre los campos `end_date`/`end_reason` del paciente: *"un paciente tiene fecha de alta cuando se crea el contacto, y no debe tener fecha de baja."*

**Cómo aplicar:**
- `active = fields.Boolean(default=True, tracking=True)` ya viene en mixins. Usar el botón Archive nativo.
- `start_date` puede ser readonly con default `context_today`. Mostrarlo como etiqueta gris bajo el nombre.

## 6. Validaciones específicas, no genéricas

**Regla:** No agregar pre-validaciones para casos hipotéticos. Solo cuando el usuario describe un caso concreto.

**Ejemplo concreto:** El usuario pidió *"un padre nunca puede ser menor que un hijo"* → agregué `_check_generational_age` solo para `parent`/`grandparent` y sus inversos. No para `spouse`, `sibling`, etc., porque esos pueden ser de cualquier edad.

## 7. Prefilling > preguntar

Cuando hay datos disponibles, prefillearlos:
- Al crear un appointment, autocompletar `coverage_id` con la primary del paciente.
- Al crear un appointment, autocompletar `duration_minutes` con la cascada profesional→especialidad→30.
- Al cargar un patient nuevo, si el DNI matchea → autocompletar nombre, fecha nac, género, teléfono, email.

## 8. Estilo de comunicación cuando hay errores

Cuando proponés una solución que falla:
- Reconocer el error sin defenderlo (*"tenés razón, fue una mala solución"*).
- Explicar la causa técnica concreta.
- Proponer el camino correcto.
- Implementar.

El usuario aprecia más eso que el "perdón, no entendí" + intento ciego.

## 9. Caché y refresh

Cuando el usuario ve algo inconsistente, antes de asumir bug:
- Verificar si es cache del browser (Ctrl+Shift+F5).
- Verificar si el servicio Odoo se reinició después del último upgrade.
- Inspeccionar la DB directamente para confirmar el estado real.

Solo después confirmar bug y fixear.
