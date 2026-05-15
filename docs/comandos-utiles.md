# Comandos útiles

PowerShell + cmd snippets para tareas típicas en este proyecto Windows.

## Upgrade del módulo (sin restart del servicio)

```powershell
& "C:\Program Files\Odoo 19\python\python.exe" "C:\Program Files\Odoo 19\server\odoo-bin" `
    -c "C:\Program Files\Odoo 19\server\odoo.conf" `
    -d dental_clinic_dev `
    -u clinic_core `
    --stop-after-init `
    --no-http `
    --log-level=error
```

`--no-http` evita conflicto de puerto con el servicio que está corriendo. `--stop-after-init` corre el upgrade y sale.

## Restart del servicio (permisos quirúrgicos ya configurados al user `loyol`)

```powershell
Restart-Service odoo-server-19.0 -Force
```

Si no tenés permisos: ver `docs/`. La opción 1 (permiso quirúrgico) se aplicó al user `loyol` una vez.

## Demo loader idempotente

```powershell
$scriptPath = "C:\Users\loyol\Work\0-Lucas\Dental-Odoo\scripts\load_demo_data.py"
$tempPath = "$env:TEMP\demo_clean.py"
$content = [System.IO.File]::ReadAllText($scriptPath, [System.Text.Encoding]::UTF8).TrimStart([char]0xFEFF)
[System.IO.File]::WriteAllText($tempPath, $content, [System.Text.UTF8Encoding]::new($false))

cmd /c "set PYTHONIOENCODING=utf-8&& set PYTHONUTF8=1&& `"C:\Program Files\Odoo 19\python\python.exe`" `"C:\Program Files\Odoo 19\server\odoo-bin`" shell -c `"C:\Program Files\Odoo 19\server\odoo.conf`" -d dental_clinic_dev --no-http --log-level=error < `"$tempPath`""
```

Necesario quitar el BOM porque Odoo shell falla si recibe `﻿` en stdin. El `PYTHONIOENCODING=utf-8` resuelve issues de caracteres acentuados en outputs.

## Queries SQL útiles

### Conexión

```powershell
$env:PGPASSWORD = "Olegari0"
& "C:\Program Files\Odoo 19\PostgreSQL\bin\psql.exe" -h localhost -p 5432 -U openpg -d dental_clinic_dev
```

### Conteos del demo

```sql
SELECT 'patients' AS m, COUNT(*) FROM clinic_patient
UNION ALL SELECT 'practitioners', COUNT(*) FROM hr_employee WHERE is_clinic_practitioner
UNION ALL SELECT 'appointments', COUNT(*) FROM clinic_appointment
UNION ALL SELECT 'coverages', COUNT(*) FROM clinic_patient_coverage
UNION ALL SELECT 'links', COUNT(*) FROM clinic_person_link
UNION ALL SELECT 'tariffs', COUNT(*) FROM clinic_tariff;
```

### Turnos de hoy (lo que el dashboard muestra)

```sql
SELECT a.start_datetime::time AS hora,
       p.medical_history_number AS hc,
       rp.name AS paciente,
       e.name AS profesional,
       a.state
FROM clinic_appointment a
JOIN clinic_patient p ON a.patient_id=p.id
JOIN res_partner rp ON p.partner_id=rp.id
JOIN hr_employee e ON a.practitioner_id=e.id
WHERE a.start_datetime::date = CURRENT_DATE
ORDER BY a.start_datetime;
```

### Verificar encoding (debugging acentos)

```sql
SELECT name, encode(name::bytea, 'hex') AS hex
FROM res_partner
WHERE name LIKE '%ndez' LIMIT 3;
```

Si los bytes son `c3 ad` para `í`, el UTF-8 es correcto. Si lo ves mal en consola, es solo display de la terminal.

## Console UTF-8 fix

Para que PowerShell/cmd muestren bien los acentos al hacer queries:

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
chcp 65001
```

## Smoke test rápido (Odoo shell)

Para probar comportamiento sin tocar la DB:

```python
# scripts/test_something.py
result = env['clinic.patient'].search([], limit=1)
print(result.name, result.medical_history_number)
env.cr.rollback()  # No persistir cambios de prueba
```

Y correr con el patrón del demo loader (`cmd /c ... shell ... < script`).

## Logs

```powershell
# Log del servicio Odoo (modo servicio)
Get-Content "C:\Program Files\Odoo 19\server\odoo.log" -Tail 50 -Wait

# Log del último upgrade manual
Get-Content "$env:TEMP\odoo_upgrade*.log" -Tail 50
```

## Git en Windows

```powershell
# Status verbose
cd "C:\Users\loyol\Work\0-Lucas\Dental-Odoo"
git status

# Commit con HEREDOC (formato preferido del proyecto)
git commit -m @'
feat(clinic_core): breve descripción

Detalle del por qué.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
'@
```

`@'...'@` es here-string single-quoted en PowerShell — preserva todo sin interpolación.

## Path importantes

| Recurso | Path |
|---|---|
| Working directory del proyecto | `C:\Users\loyol\Work\0-Lucas\Dental-Odoo` |
| Source de Odoo 19 (read-only) | `C:\Program Files\Odoo 19\server\` |
| Addons nativos | `C:\Program Files\Odoo 19\server\odoo\addons\` |
| Config del servicio | `C:\Program Files\Odoo 19\server\odoo.conf` |
| Python de Odoo | `C:\Program Files\Odoo 19\python\python.exe` |
| Postgres bin | `C:\Program Files\Odoo 19\PostgreSQL\bin\` |
| Log del servicio | `C:\Program Files\Odoo 19\server\odoo.log` |
| Análisis previo (referencia) | `C:\Users\loyol\Work\0-Lucas\ClinicBot\docs\` |
