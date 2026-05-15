# Invariantes no negociables

Reglas estructurales heredadas del análisis previo (ClinicBot, archivado) que aplican a Dental-Odoo. Son **no negociables** sin reabrir discusión explícita.

## 1. Multi-tenancy desde V1
Toda tabla operativa lleva `company_id`. En Odoo se traduce a `res.company` + record rules nativas. En V1 hay 1 sola company pero el modelo está preparado para múltiples.

## 2. Postgres = fuente única de verdad
Cualquier servicio externo (Google Calendar, WhatsApp, integraciones) es **espejo**. Nada externo decide algo que la DB no sabe.

## 3. Modelo Persona / Paciente / Contacto / Vínculo separados (conceptualmente)
- Persona = humano (`res.partner` con `is_clinic_person=True`).
- Paciente = subentidad de Persona (`clinic.patient` con `_inherits res.partner`, per-company).
- Contacto = canal (refactorizado 2026-05-15: ahora es el `phone`/`email` nativo del partner, no entidad separada).
- Vínculo = relación humana (`clinic.person.link` con bidi automático).

## 4. Slots on-the-fly (NO pre-generados — cambio del invariante ClinicBot)
Disponibilidad se calcula desde `resource.calendar` + turnos existentes. Ver decisión D.

## 5. Sync Calendar unidireccional
Cuando se implemente (V2): Odoo → Google Calendar. Nunca al revés.

## 6. Bot identificado + comando "humano" siempre disponible
Cuando se implemente el bot (V2): se identifica como virtual al inicio de cada sesión. La palabra "humano" escala determinísticamente sin pasar por LLM.

## 7. Casos sensibles con templates fijos
Mensajes iniciales en urgencia / salud mental / violencia / menor = templates pre-aprobadas, NO LLM. Mensajes posteriores pueden usar LLM con guardrails. (V2 con bot.)

## 8. Audit log mínimo desde V1
Cambios en `clinic.appointment` y `clinic.patient` se trackean. Mapeado a `mail.thread` + `tracking=True` en campos críticos.

## 9. Cobertura compartida
Un paciente puede tener N obras sociales simultáneas (ej. menor con OSDE del padre + Galeno de la madre). `clinic.patient.coverage.holder_partner_id` puede apuntar a una persona que NO es paciente.

## 10. Vías de facturación (DIRECTO / ASOR / AOSS)
Una OS + vía se factura distinto según convenio. Tarifarios versionados con `valid_from`. AOSS = Asoc. Odontológica San Lorenzo Sud (Pujato), real.

## 11. Catálogo FACO con códigos `CC.SS.NN`
Única fuente de verdad para identificar prácticas. OS con códigos propios (ej. AVALIAN 346027 para Cefalometría) se mapean en `clinic.practice.code.os`.

## 12. Soft delete por defecto
Casi nada se borra. `active=False` (Odoo nativo) en lugar de `end_date`/`archived_at` custom.

## 13. Datos sensibles NO van por WhatsApp
HIV, salud mental, datos clínicos detallados — aunque el contacto esté autorizado. Compliance Ley 26.529.

## 14. Compliance argentino
- Ley 25.326 (datos personales) — datos en AR o EU
- Ley 26.529 (HC) — retención 10 años post última consulta, derecho del paciente a copia

## Cómo aplicar

Si una decisión Odoo idiomática choca con un invariante (ej. tentación de meter todo en `res.partner` ignorando la separación Persona/Paciente), **parar y discutir** con el usuario. No asumir override.
