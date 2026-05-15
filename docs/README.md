# Documentación del proyecto

Documentación viva. Actualizar al cambiar decisiones estructurales.

## Índice

| Doc | Para qué |
|---|---|
| [`invariantes.md`](invariantes.md) | Reglas estructurales no negociables (multi-tenancy, Postgres SoT, casos sensibles, etc.) |
| [`decisiones-modelo.md`](decisiones-modelo.md) | Decisiones A-O sobre cómo mapear el dominio a Odoo. Cambiarlas requiere abrir discusión. |
| [`convenciones.md`](convenciones.md) | Naming, encoding, timezones, patrones técnicos del proyecto |
| [`estado-actual.md`](estado-actual.md) | Snapshot al último commit: módulos, modelos, demo data, próximos pasos |
| [`lecciones-ux.md`](lecciones-ux.md) | Patrones de UX aprendidos. Aplicar de oficio, sin esperar pedido. |
| [`comandos-utiles.md`](comandos-utiles.md) | PowerShell snippets para upgrade, demo loader, queries útiles |

## Cuándo leer estos docs

- **Al entrar al proyecto** (fresh session, after `/clear`): leer [`../CLAUDE.md`](../CLAUDE.md) primero, después este índice.
- **Antes de proponer cambios al modelo**: releer `decisiones-modelo.md` para no contradecirlas.
- **Antes de codear flujos UX**: releer `lecciones-ux.md`.
- **Cuando dudás de un patrón técnico**: `convenciones.md`.

## Cómo evoluciona la documentación

- Decisiones nuevas → entrada en `decisiones-modelo.md` con letra siguiente (P, Q, ...).
- Después de cada slice mayor → update `estado-actual.md`.
- Cuando el usuario corrige un comportamiento UX → entrada en `lecciones-ux.md`.
- Convenciones nuevas verificadas en v19 source → `convenciones.md`.
