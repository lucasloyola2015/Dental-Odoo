# Dental-Odoo

Sistema de gestión clínica multi-profesional sobre **Odoo 19 Community**.
Proyecto oficial de Lucas Loyola para la clínica dental de su esposa (Roldán, Santa Fe, AR).

> Este archivo es el primer contexto que lee Claude al entrar al repo. Es corto a propósito.
> Para detalles, los docs están en [`docs/`](docs/).

## Qué hay en el proyecto

```
custom_addons/
  clinic_core/    Núcleo del módulo (16 modelos, ver docs/estado-actual.md)
  clinic_dental/  Extensión dental (scaffold vacío todavía)
scripts/
  load_demo_data.py   Loader idempotente de datos demo
docs/
  Documentación viva — leer antes de proponer cambios estructurales
```

**Stack**: Odoo 19 + PostgreSQL 12 (local Windows en `C:\Program Files\Odoo 19\`).
Base de datos de trabajo: `dental_clinic_dev`.

## Cómo trabajar conmigo en este proyecto

### Reglas no negociables

1. **Verificar Odoo 19 antes de invocar.** Las APIs cambian entre versiones. Si dudo de un campo/método, lo busco en el source local antes de escribir código. Ver [`docs/convenciones.md`](docs/convenciones.md).
2. **Reutilizar modelos Odoo nativos.** No duplicar — si existe `res.partner`, usarlo (extender o vincular). Ver decisiones en [`docs/decisiones-modelo.md`](docs/decisiones-modelo.md).
3. **No reinventar la rueda.** Antes de diseñar, mirar cómo lo resuelven los players profesionales (Doctolib, Cliniko, SimplePractice, FHIR, OCA medical).
4. **Sistema piensa, usuario no recuerda.** Si el sistema puede deducir algo, NO preguntar al usuario. Ver [`docs/lecciones-ux.md`](docs/lecciones-ux.md).
5. **Si dudás, preguntá.** Mejor 3 preguntas que generar código que después hay que deshacer. Cosas que siempre se preguntan: cambios al modelo de datos, decisiones UX sin spec, agregar dependencia, lógica de scheduling/identificación.

### Estilo

- **Chat**: español rioplatense con voseo. Conciso. Sin essays.
- **Código y commits**: inglés.
- **Mensajes al paciente** (templates futuros): español rioplatense.
- **Respuestas**: si hay 3 trade-offs, listarlos breves. No 3 párrafos cada uno.

### Antes de tirar código largo

Proponer **plan en alto nivel** y esperar OK. Para cambios estructurales (modelos nuevos, refactor de vistas, decisiones de modelado), parar y discutir primero.

## Snapshot rápido

- **25 commits** trabajados.
- **Demo data cargado** en `dental_clinic_dev`: 12 pacientes, 4 profesionales, 21 turnos, 16 tarifas AVALIAN reales.
- **Core operativo V1** completo: paciente → buscar disponibilidad → agendar → atender → ver presupuesto.

Ver [`docs/estado-actual.md`](docs/estado-actual.md) para el snapshot detallado.

## Comandos rápidos (Windows PowerShell)

```powershell
# Upgrade del módulo
& "C:\Program Files\Odoo 19\python\python.exe" "C:\Program Files\Odoo 19\server\odoo-bin" -c "C:\Program Files\Odoo 19\server\odoo.conf" -d dental_clinic_dev -u clinic_core --stop-after-init --no-http --log-level=error

# Restart del servicio (permisos quirúrgicos ya configurados al user loyol)
Restart-Service odoo-server-19.0 -Force
```

Ver [`docs/comandos-utiles.md`](docs/comandos-utiles.md) para más.

## Cosas que NO hacer

- ❌ Usar APIs muertas o renombradas (verificar v19 source primero).
- ❌ Crear modelos custom cuando un nativo de Odoo / OCA sirve.
- ❌ Preguntar al usuario datos que el sistema puede deducir (DNI lookup, cascada de duración, etc.).
- ❌ Forms con 50 campos. Crear vistas custom mínimas para flujos clínicos.
- ❌ Duplicar `res.partner` cuando un paciente nuevo coincide con un contacto existente — reusar via DNI.
- ❌ Saltarse `git status` antes de commit. Nunca commitear sin diff revisado.
- ❌ Inventar APIs de bases públicas (RENAPER/AFIP) sin verificar primero.

## Antes de cada commit

- [ ] El upgrade `-u clinic_core` corre sin ERRORs ni CRITICALs.
- [ ] El demo loader sigue funcionando.
- [ ] Si toqué modelos, verifico que los datos demo siguen sanos (`patients`, `appointments`, etc.).
- [ ] Mensaje de commit en inglés, formato `<tipo>(scope): descripción` + cuerpo explicando el porqué.
- [ ] Co-Authored-By footer.
- [ ] **Nunca commitear sin que el usuario lo pida** explícitamente.

## Memoria personal (no en repo)

Mi memoria personal de Claude vive en `~/.claude/projects/.../memory/`. Es por-máquina y no se versiona. Apunta a este repo para detalle.
