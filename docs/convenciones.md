# Convenciones técnicas

## Naming

| Cosa | Convención | Ejemplo |
|---|---|---|
| Modelos | `clinic.<entidad>` o extensión Odoo | `clinic.patient`, `hr.employee` |
| Campos | `snake_case` en inglés | `medical_history_number` |
| Variables / funciones Python | `snake_case` | `get_available_slots` |
| Constantes | `UPPER_SNAKE_CASE` | `INVERSE_TYPE`, `A_OLDER_THAN_B` |
| External IDs (xmlid) | `<module>.<name>` snake_case | `clinic_core.specialty_odontologia` |
| Labels en UI | español neutro | `"N° Historia Clínica"`, `"DNI"` |
| Mensajes al paciente | español rioplatense con voseo | `"Te confirmamos el turno..."` |
| Commits | inglés, formato `<tipo>(scope): descripción` | `feat(clinic_core): add age field` |

## Encoding

- **Archivos Python/XML**: UTF-8 sin BOM. Si la herramienta los crea con BOM, hay que stripearlo al pasar via stdin a `odoo-bin shell` (`TrimStart([char]0xFEFF)`).
- **DB**: server_encoding y client_encoding = UTF8 (verificado).
- **PowerShell console** muestra mal UTF-8 por default. Para ver bien:
  ```powershell
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
  chcp 65001
  ```

## Timezones

- **DB**: Datetime fields en UTC naive (Odoo nativo).
- **Presentación**: `America/Argentina/Buenos_Aires` (config del user).
- **Importante en v19**: `resource.calendar._work_intervals_batch()` requiere datetimes **tz-aware**. Antes de llamar:
  ```python
  user_tz = pytz.timezone(self.env.user.tz or "UTC")
  dt_aware = user_tz.localize(dt_naive) if dt_naive.tzinfo is None else dt_naive
  ```

## Multi-company

- Catálogos compartidos: `company_id = fields.Many2one('res.company', index=True)` (opcional, no required). Si vacío = global.
- Per-company: `company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)`.
- Many2one cross-model dentro de mismo company: agregar `check_company=True` y al modelo `_check_company_auto = True`.

## Reglas de desarrollo Odoo 19 (no negociables)

### Regla A — Verificar antes de invocar
Antes de usar cualquier modelo, campo, método o decorator de Odoo, verificar su existencia y nomenclatura **en Odoo 19**.

Source local en `C:\Program Files\Odoo 19\server\odoo\addons\`.

**Cambios conocidos v17/18 → v19**:
- `res.partner.mobile` **NO existe** en v19. Solo `phone`.
- `res.groups.category_id` reemplazado por `privilege_id` (apunta a nuevo modelo `res.groups.privilege`).
- `<group string="...">` dentro de `<search>` **NO es válido**. Sin `string`.
- Vista list root es `<list>` (no `<tree>`).
- `_check_recursion()` deprecado → usar `_has_cycle()` (semántica invertida).
- `_sql_constraints` reemplazado por `models.Constraint('sql', 'msg')` como class attribute.
- `_parent_store = True` requiere declarar `parent_path = fields.Char(index=True)` (sin parámetro `unaccent`).
- `_attendance_intervals_batch` y `_work_intervals_batch` requieren datetimes **tz-aware**.
- `name_search` firma cambió: `name='', domain=None, operator='ilike', limit=100` (era `args` en v17).

### Regla B — Reutilizar Odoo nativo, no duplicar
Antes de crear un modelo nuevo, evaluar:
- `res.partner` para personas/contactos
- `res.company` para organizaciones
- `res.users` para usuarios del sistema
- `hr.employee` para empleados
- `resource.calendar` para horarios
- `calendar.event` para eventos calendar (con limitaciones, ver decisión C)
- `mail.thread` para audit + chatter
- `product.template` para productos/servicios
- `l10n_latam.identification.type` (con `l10n_ar`) para tipos de documento AR

Si no encaja → modelo nuevo, justificando explícitamente.

### Regla C — No reinventar
Antes de diseñar un patrón nuevo, investigar:
- Cómo lo resuelven SaaS profesionales (Doctolib, Cliniko, SimplePractice)
- Estándares aplicables (FHIR, HL7)
- Módulos OCA relevantes
- Módulos Odoo nativos del rubro

## Patrones del proyecto

### Modelos custom: structure base

```python
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ClinicSomething(models.Model):
    _name = "clinic.something"
    _description = "..."
    _inherit = ["mail.thread"]  # cuando queremos audit
    _order = "..."
    _rec_name = "display_name"  # cuando display_name es computed
    _check_company_auto = True  # cuando hay company_id

    field = fields.Char(string="...", required=True, tracking=True)
    company_id = fields.Many2one("res.company", ...)

    _unique_constraint = models.Constraint(
        "unique (field, company_id)",
        "Mensaje en español.",
    )

    @api.depends("field")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"..."
```

### Vistas: form custom para flujos clínicos

- NO heredar la vista nativa de hr.employee/res.partner para flujos clínicos.
- Crear vista form NUEVA (no inherit) y forzarla via `view_ids` en la action.
- Mostrar SOLO los campos relevantes. No `oe_avatar` (genera bloque extra).
- Cabecera: name editable + readonly labels (matrícula, DNI, etc.).
- Datos editables en grupos del cuerpo.

### Loops de sincronización

Cuando hay sync bidireccional (ej. `hr.employee.name` ↔ `res.partner.name`):
- Usar context flag para break loop: `_syncing_name`.
- Ambos models check el flag antes de propagar.

```python
def write(self, vals):
    res = super().write(vals)
    if "name" in vals and not self.env.context.get("_syncing_name"):
        for emp in self:
            emp.work_contact_id.with_context(_syncing_name=True).name = emp.name
    return res
```

## Comandos a evitar

- ❌ `git add .` o `git add -A` sin verificar. Mejor `git add <files>` específicos.
- ❌ `--no-verify` en commits. Si falla pre-commit, fixear la causa.
- ❌ `git rebase -i` o `git add -i` (interactive, no soportado por el agent).
- ❌ `git push --force` a main.
- ❌ Modificar archivos en `C:\Program Files\Odoo 19\` (es el source nativo, read-only para el proyecto).
