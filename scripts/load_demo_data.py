"""
Demo data loader for clinic_core.

Run via Odoo shell:
    odoo-bin shell -c <odoo.conf> -d <db> --no-http < scripts/load_demo_data.py

Idempotent: deletes previous demo records (matched by HC numbers HC-0001..HC-0009
and by the resource.calendar name) before creating fresh ones.
"""

from datetime import date, datetime, time, timedelta

print("=" * 60)
print("Loading clinic demo data...")
print("=" * 60)

main_company = env.company
print(f"Company: {main_company.name}")

# =============================================================================
# CLEANUP previous demo records
# =============================================================================
print("\n[1/7] Cleaning up previous demo data...")

demo_hc_numbers = [f"HC-{i:04d}" for i in range(1, 10)]
demo_patients = env["clinic.patient"].with_context(active_test=False).search(
    [("medical_history_number", "in", demo_hc_numbers)]
)
demo_partner_ids = demo_patients.partner_id.ids
pedro = env["res.partner"].search([("vat", "=", "22567890")], limit=1)
if pedro:
    demo_partner_ids += pedro.ids

if demo_patients or pedro:
    appts = env["clinic.appointment"].with_context(active_test=False).search([
        ("patient_id", "in", demo_patients.ids),
    ])
    print(f"  Deleting {len(appts)} appointments...")
    appts.unlink()

    coverages = env["clinic.patient.coverage"].with_context(active_test=False).search([
        ("patient_id", "in", demo_patients.ids),
    ])
    print(f"  Deleting {len(coverages)} coverages...")
    coverages.unlink()

    # person links: both directions (mirrors auto-deleted via unlink override)
    links = env["clinic.person.link"].with_context(active_test=False).search([
        "|", ("partner_a_id", "in", demo_partner_ids),
             ("partner_b_id", "in", demo_partner_ids),
    ])
    print(f"  Deleting {len(links)} person links (mirrors cascade)...")
    links.unlink()

    print(f"  Deleting {len(demo_patients)} patients...")
    demo_patients.unlink()
    if pedro:
        pedro.unlink()

# Cleanup practitioners + roles + practitioner-practices
demo_employees = env["hr.employee"].with_context(active_test=False).search([
    ("medical_license", "in", ["MP 12345 (SF)", "MP 67890 (SF)", "MP 99999 (SF)"]),
])
if demo_employees:
    pp = env["clinic.practitioner.practice"].with_context(active_test=False).search([
        ("employee_id", "in", demo_employees.ids),
    ])
    print(f"  Deleting {len(pp)} practitioner-practices...")
    pp.unlink()
    roles = env["clinic.practitioner.role"].with_context(active_test=False).search([
        ("employee_id", "in", demo_employees.ids),
    ])
    print(f"  Deleting {len(roles)} practitioner roles...")
    roles.unlink()
    print(f"  Deleting {len(demo_employees)} employees...")
    demo_employees.unlink()

# Cleanup resource calendar
demo_calendar = env["resource.calendar"].with_context(active_test=False).search([
    ("name", "=", "Horario Clínica L-V 9-13/14-18 (demo)"),
])
if demo_calendar:
    print(f"  Deleting demo resource.calendar...")
    demo_calendar.unlink()

# =============================================================================
# RESOURCE CALENDAR
# =============================================================================
print("\n[2/7] Creating resource.calendar...")

attendances = []
for dow in range(5):  # Monday=0..Friday=4
    attendances.append((0, 0, {
        "name": "Mañana",
        "dayofweek": str(dow),
        "hour_from": 9.0,
        "hour_to": 13.0,
        "day_period": "morning",
    }))
    attendances.append((0, 0, {
        "name": "Tarde",
        "dayofweek": str(dow),
        "hour_from": 14.0,
        "hour_to": 18.0,
        "day_period": "afternoon",
    }))

calendar = env["resource.calendar"].create({
    "name": "Horario Clínica L-V 9-13/14-18 (demo)",
    "tz": "America/Argentina/Buenos_Aires",
    "attendance_ids": attendances,
    "company_id": main_company.id,
})
print(f"  Created calendar: {calendar.name}")

# =============================================================================
# PRACTITIONERS
# =============================================================================
print("\n[3/7] Creating practitioners...")

spec_odonto = env.ref("clinic_core.specialty_odontologia")
spec_odonto_ped = env.ref("clinic_core.specialty_odontopediatria")
spec_endo = env.ref("clinic_core.specialty_endodoncia")
spec_orto = env.ref("clinic_core.specialty_ortodoncia")
spec_perio = env.ref("clinic_core.specialty_periodoncia")
spec_cirug = env.ref("clinic_core.specialty_cirugia_oral")

route_aoss = env.ref("clinic_core.billing_route_aoss")
route_directo = env.ref("clinic_core.billing_route_directo")

hi_avalian = env.ref("clinic_core.health_insurance_avalian")
hi_iapos = env.ref("clinic_core.health_insurance_iapos")
hi_osde = env.ref("clinic_core.health_insurance_osde")
hi_swiss = env.ref("clinic_core.health_insurance_swiss")
hi_particular = env.ref("clinic_core.health_insurance_particular")
hi_galeno = env.ref("clinic_core.health_insurance_galeno")

dra_tenaglia = env["hr.employee"].create({
    "name": "Dra. Laura Tenaglia",
    "is_clinic_practitioner": True,
    "medical_license": "MP 12345 (SF)",
    "specialty_main_id": spec_odonto.id,
    "specialty_ids": [(6, 0, [spec_odonto.id, spec_odonto_ped.id, spec_perio.id])],
    "default_appointment_duration_minutes": 30,
    "slots_buffer_post_minutes": 0,
    "work_email": "laura.tenaglia@example.com",
    "clinic_observations": "Atiende niños y adultos. Trabaja en periodoncia con ficha completa.",
})

env["clinic.practitioner.role"].create({
    "employee_id": dra_tenaglia.id,
    "company_id": main_company.id,
    "resource_calendar_id": calendar.id,
    "accepted_insurance_ids": [(6, 0, [hi_avalian.id, hi_osde.id, hi_swiss.id, hi_iapos.id, hi_particular.id])],
    "billing_route_ids": [(6, 0, [route_aoss.id, route_directo.id])],
    "calendar_color": "#1f77b4",
})

dr_soto = env["hr.employee"].create({
    "name": "Dr. Martín Soto",
    "is_clinic_practitioner": True,
    "medical_license": "MP 67890 (SF)",
    "specialty_main_id": spec_endo.id,
    "specialty_ids": [(6, 0, [spec_endo.id, spec_odonto.id])],
    "default_appointment_duration_minutes": 60,
    "slots_buffer_post_minutes": 5,
    "work_email": "martin.soto@example.com",
    "clinic_observations": "Endodoncias bajo microscopio. 5 min de buffer entre turnos.",
})

env["clinic.practitioner.role"].create({
    "employee_id": dr_soto.id,
    "company_id": main_company.id,
    "resource_calendar_id": calendar.id,
    "accepted_insurance_ids": [(6, 0, [hi_avalian.id, hi_osde.id, hi_iapos.id, hi_particular.id])],
    "billing_route_ids": [(6, 0, [route_aoss.id, route_directo.id])],
    "calendar_color": "#ff7f0e",
})

dra_cardozo = env["hr.employee"].create({
    "name": "Dra. Ana Cardozo",
    "is_clinic_practitioner": True,
    "medical_license": "MP 99999 (SF)",
    "specialty_main_id": spec_orto.id,
    "specialty_ids": [(6, 0, [spec_orto.id, spec_cirug.id])],
    "default_appointment_duration_minutes": 45,
    "slots_buffer_post_minutes": 0,
    "work_email": "ana.cardozo@example.com",
})

env["clinic.practitioner.role"].create({
    "employee_id": dra_cardozo.id,
    "company_id": main_company.id,
    "resource_calendar_id": calendar.id,
    "accepted_insurance_ids": [(6, 0, [hi_avalian.id, hi_osde.id, hi_swiss.id, hi_galeno.id, hi_particular.id])],
    "billing_route_ids": [(6, 0, [route_aoss.id, route_directo.id])],
    "calendar_color": "#2ca02c",
})

print(f"  Created 3 practitioners.")

practitioner_practices = [
    (dra_tenaglia, "practice_01_01", 30000, 30),
    (dra_tenaglia, "practice_01_04", 35000, 30),
    (dra_tenaglia, "practice_02_01", 50000, 45),
    (dra_tenaglia, "practice_02_02", 70000, 60),
    (dra_tenaglia, "practice_02_03", 95000, 75),
    (dra_tenaglia, "practice_05_01", 40000, 30),
    (dra_tenaglia, "practice_05_02", 20000, 15),
    (dra_tenaglia, "practice_05_04", 30000, 30),
    (dra_tenaglia, "practice_05_05", 22000, 15),
    (dra_tenaglia, "practice_07_01", 35000, 30),
    (dra_tenaglia, "practice_08_01", 40000, 45),
    (dra_tenaglia, "practice_08_02", 80000, 60),

    (dr_soto, "practice_01_01", 35000, 30),
    (dr_soto, "practice_03_01", 110000, 60),
    (dr_soto, "practice_03_02", 170000, 75),
    (dr_soto, "practice_03_03", 195000, 90),
    (dr_soto, "practice_03_04", 230000, 90),
    (dr_soto, "practice_03_05", 80000, 45),
    (dr_soto, "practice_03_06", 70000, 45),

    (dra_cardozo, "practice_01_01", 35000, 30),
    (dra_cardozo, "practice_09_02_05", 40000, 30),
    (dra_cardozo, "practice_09_02_07", 45000, 30),
    (dra_cardozo, "practice_10_01", 55000, 30),
    (dra_cardozo, "practice_10_06", 65000, 45),
    (dra_cardozo, "practice_10_09", 150000, 75),
]

for emp, prac_xmlid, price, duration in practitioner_practices:
    env["clinic.practitioner.practice"].create({
        "employee_id": emp.id,
        "practice_id": env.ref(f"clinic_core.{prac_xmlid}").id,
        "company_id": main_company.id,
        "can_perform": True,
        "price_particular": price,
        "default_duration_minutes": duration,
    })
print(f"  Created {len(practitioner_practices)} practitioner-practice rows.")

# =============================================================================
# PATIENTS + Pedro (non-patient Person, OSDE holder)
# =============================================================================
print("\n[4/7] Creating patients + Pedro (Persona only)...")

# Pedro Méndez — Persona, NO Paciente. Titular OSDE de sus hijos. Su phone es de él.
pedro = env["res.partner"].create({
    "name": "Pedro Méndez",
    "is_clinic_person": True,
    "birthdate": date(1975, 3, 15),
    "gender": "male",
    "vat": "22567890",
    "phone": "+5493455555555",
    "email": "pedro.mendez@example.com",
})
print(f"  Created Persona (not Patient): {pedro.name}")

carlos = env["clinic.patient"].create({
    "name": "Carlos Pérez",
    "is_clinic_person": True,
    "birthdate": date(1980, 5, 10),
    "gender": "male",
    "vat": "25123456",
    "phone": "+5493411111111",
    "email": "carlos.perez@example.com",
    "company_id": main_company.id,
    "secretariat_notes": "Particular. Buen cumplidor de turnos.",
})

maria = env["clinic.patient"].create({
    "name": "María López",
    "is_clinic_person": True,
    "birthdate": date(1985, 8, 22),
    "gender": "female",
    "vat": "30234567",
    "phone": "+5493422222222",
    "email": "maria.lopez@example.com",
    "company_id": main_company.id,
})

juan = env["clinic.patient"].create({
    "name": "Juan García",
    "is_clinic_person": True,
    "birthdate": date(1983, 2, 5),
    "gender": "male",
    "vat": "28345678",
    "phone": "+5493433333333",
    "company_id": main_company.id,
})

ana = env["clinic.patient"].create({
    "name": "Ana Sosa",
    "is_clinic_person": True,
    "birthdate": date(1988, 11, 30),
    "gender": "female",
    "vat": "32456789",
    "phone": "+5493444444444",
    "company_id": main_company.id,
    "secretariat_notes": "Tiene IAPOS principal y Swiss Medical complementaria.",
})

# Sofía Méndez (7) — menor, sin phone propio. use_external_contact=True
# La validación del constraint requiere que YA exista el link al padre con can_be_contacted=True
# antes de marcar use_external_contact. Por eso primero creamos sin flag, después agregamos
# link y por último activamos use_external_contact.
sofia = env["clinic.patient"].create({
    "name": "Sofía Méndez",
    "is_clinic_person": True,
    "birthdate": date(2018, 6, 1),
    "gender": "female",
    "vat": "50678901",
    "phone": "+5493411000001",  # temporal — luego limpiamos cuando seteemos use_external_contact
    "company_id": main_company.id,
    "secretariat_notes": "Menor. Comunicaciones al padre Pedro Méndez.",
})

lucas = env["clinic.patient"].create({
    "name": "Lucas Méndez",
    "is_clinic_person": True,
    "birthdate": date(2014, 4, 18),
    "gender": "male",
    "vat": "48789012",
    "phone": "+5493411000002",  # temporal
    "company_id": main_company.id,
    "secretariat_notes": "Menor. Comunicaciones al padre Pedro Méndez.",
})

rosa = env["clinic.patient"].create({
    "name": "Doña Rosa Fernández",
    "is_clinic_person": True,
    "birthdate": date(1948, 9, 12),
    "gender": "female",
    "vat": "8890123",
    "phone": "+5493466666666",
    "company_id": main_company.id,
    "secretariat_notes": "Jubilada. Atiende los martes preferentemente.",
})

roberto = env["clinic.patient"].create({
    "name": "Roberto Vázquez",
    "is_clinic_person": True,
    "birthdate": date(1955, 7, 3),
    "gender": "male",
    "vat": "10901234",
    "phone": "+5493477777777",
    "company_id": main_company.id,
})

patients_all = [carlos, maria, juan, ana, sofia, lucas, rosa, roberto]
print(f"  Created {len(patients_all)} patients.")

# =============================================================================
# PERSON LINKS (Pedro → Sofía/Lucas with can_be_contacted=True)
# =============================================================================
print("\n[5/7] Creating person links (mirrors auto-generated)...")

env["clinic.person.link"].create([
    {
        "partner_a_id": pedro.id,
        "partner_b_id": sofia.partner_id.id,
        "relationship_type": "parent",
        "is_legal_guardian": True,
        "can_consent": True,
        "can_be_contacted": True,
    },
    {
        "partner_a_id": pedro.id,
        "partner_b_id": lucas.partner_id.id,
        "relationship_type": "parent",
        "is_legal_guardian": True,
        "can_consent": True,
        "can_be_contacted": True,
    },
])
print(f"  Created 2 person links (Pedro → Sofía, Pedro → Lucas) + 2 mirrors auto.")

# Now that links exist with can_be_contacted=True, switch Sofía and Lucas to external contact
sofia.write({"phone": False, "email": False, "use_external_contact": True})
lucas.write({"phone": False, "email": False, "use_external_contact": True})
print(f"  Switched Sofía and Lucas to use_external_contact=True.")

# =============================================================================
# COVERAGES
# =============================================================================
print("\n[6/7] Creating coverages...")

env["clinic.patient.coverage"].create([
    {
        "patient_id": maria.id,
        "health_insurance_id": hi_osde.id,
        "member_number": "OSDE-30234567-01",
        "plan": "310",
        "is_holder": True,
        "os_relationship": "titular",
        "is_primary": True,
    },
    {
        "patient_id": juan.id,
        "health_insurance_id": hi_avalian.id,
        "member_number": "AVL-28345678",
        "plan": "Plan Base",
        "is_holder": True,
        "os_relationship": "titular",
        "is_primary": True,
    },
    {
        "patient_id": ana.id,
        "health_insurance_id": hi_iapos.id,
        "member_number": "IAPOS-32456789",
        "plan": "Plan A",
        "is_holder": True,
        "os_relationship": "titular",
        "is_primary": True,
        "order": 1,
    },
    {
        "patient_id": ana.id,
        "health_insurance_id": hi_swiss.id,
        "member_number": "SW-32456789",
        "plan": "SMG-300",
        "is_holder": True,
        "os_relationship": "titular",
        "is_primary": False,
        "order": 2,
    },
    {
        "patient_id": sofia.id,
        "health_insurance_id": hi_osde.id,
        "member_number": "OSDE-22567890-02",
        "plan": "310",
        "is_holder": False,
        "holder_partner_id": pedro.id,
        "os_relationship": "child",
        "is_primary": True,
    },
    {
        "patient_id": lucas.id,
        "health_insurance_id": hi_osde.id,
        "member_number": "OSDE-22567890-03",
        "plan": "310",
        "is_holder": False,
        "holder_partner_id": pedro.id,
        "os_relationship": "child",
        "is_primary": True,
    },
    {
        "patient_id": rosa.id,
        "health_insurance_id": hi_iapos.id,
        "member_number": "IAPOS-8890123",
        "is_holder": True,
        "os_relationship": "titular",
        "is_primary": True,
    },
])
print(f"  Created 7 coverages.")

# =============================================================================
# APPOINTMENTS
# =============================================================================
print("\n[7/7] Creating appointments...")

today = date.today()
today_dt = datetime.combine(today, time(9, 0))

def appt(patient, practitioner, practice_xmlid, start_dt, duration, state, **kw):
    practice = env.ref(f"clinic_core.{practice_xmlid}")
    coverage = patient.coverage_ids.filtered(lambda c: c.is_primary)[:1]
    vals = {
        "patient_id": patient.id,
        "practitioner_id": practitioner.id,
        "practice_id": practice.id,
        "start_datetime": start_dt,
        "duration_minutes": duration,
        "state": state,
        "company_id": main_company.id,
    }
    if coverage:
        vals["coverage_id"] = coverage.id
        vals["billing_route_id"] = route_aoss.id
    else:
        vals["billing_route_id"] = route_directo.id
    vals.update(kw)
    return env["clinic.appointment"].create(vals)

# Hoy: 5 turnos
appt(carlos, dra_tenaglia, "practice_05_01", today_dt.replace(hour=9, minute=0), 30, "fulfilled",
     appointment_reason="Limpieza semestral.")
appt(maria, dra_tenaglia, "practice_02_01", today_dt.replace(hour=9, minute=30), 45, "fulfilled",
     appointment_reason="Caries molar superior derecho.")
appt(juan, dr_soto, "practice_03_01", today_dt.replace(hour=10, minute=30), 60, "booked",
     appointment_reason="Dolor en pieza 26, posible endodoncia.")
appt(sofia, dra_tenaglia, "practice_07_01", today_dt.replace(hour=11, minute=30), 30, "checked-in",
     appointment_reason="Control general y motivación.")
appt(ana, dra_tenaglia, "practice_05_01", today_dt.replace(hour=15, minute=0), 30, "pending",
     appointment_reason="Profilaxis. La paciente confirma por WhatsApp.")

# Mañana y próximos días
tmrw = today + timedelta(days=1)
appt(lucas, dra_tenaglia, "practice_05_02", datetime.combine(tmrw, time(10, 0)), 15, "booked",
     appointment_reason="Flúor + control.")
appt(rosa, dra_tenaglia, "practice_08_01", datetime.combine(tmrw, time(10, 30)), 45, "booked",
     appointment_reason="Sangrado de encías al cepillar.")
appt(roberto, dr_soto, "practice_03_02", datetime.combine(tmrw, time(14, 0)), 75, "pending",
     appointment_reason="Tratamiento endodóntico pieza 35.")

day_plus2 = today + timedelta(days=2)
appt(juan, dr_soto, "practice_03_01", datetime.combine(day_plus2, time(9, 0)), 60, "booked",
     appointment_reason="Continuación endodoncia.")
appt(maria, dra_cardozo, "practice_09_02_07", datetime.combine(day_plus2, time(11, 0)), 30, "pending",
     appointment_reason="Estudio de ortodoncia.")

day_plus3 = today + timedelta(days=3)
appt(carlos, dra_tenaglia, "practice_02_02", datetime.combine(day_plus3, time(15, 0)), 60, "booked",
     appointment_reason="Caries compuesta molar inferior.")

# Pasado
yesterday = today - timedelta(days=1)
appt(rosa, dra_tenaglia, "practice_01_01", datetime.combine(yesterday, time(10, 0)), 30, "fulfilled",
     appointment_reason="Primera consulta.")
appt(ana, dra_tenaglia, "practice_05_01", datetime.combine(yesterday, time(11, 0)), 30, "fulfilled")
appt(carlos, dra_tenaglia, "practice_05_01", datetime.combine(yesterday, time(15, 30)), 30, "cancelled",
     cancellation_reason="Paciente avisó que no puede.")

days_ago_7 = today - timedelta(days=7)
appt(maria, dra_tenaglia, "practice_05_01", datetime.combine(days_ago_7, time(9, 0)), 30, "fulfilled")
appt(juan, dra_tenaglia, "practice_01_01", datetime.combine(days_ago_7, time(10, 0)), 30, "fulfilled")
appt(ana, dra_tenaglia, "practice_05_01", datetime.combine(days_ago_7, time(11, 0)), 30, "noshow")
appt(lucas, dra_tenaglia, "practice_07_01", datetime.combine(days_ago_7, time(15, 0)), 30, "fulfilled")

days_ago_14 = today - timedelta(days=14)
appt(carlos, dra_tenaglia, "practice_05_01", datetime.combine(days_ago_14, time(9, 0)), 30, "fulfilled")
appt(roberto, dra_cardozo, "practice_10_01", datetime.combine(days_ago_14, time(15, 0)), 30, "fulfilled")

days_ago_21 = today - timedelta(days=21)
appt(juan, dr_soto, "practice_03_02", datetime.combine(days_ago_21, time(10, 0)), 75, "noshow")

print(f"  Created appointments across today, future and past.")

env.cr.commit()

print("\n" + "=" * 60)
print("DEMO DATA LOADED SUCCESSFULLY")
print("=" * 60)
print(f"Patients:                  {env['clinic.patient'].search_count([])}")
print(f"Persons (res.partner):     {env['res.partner'].search_count([('is_clinic_person', '=', True)])}")
print(f"Practitioners:             {env['hr.employee'].search_count([('is_clinic_practitioner', '=', True)])}")
print(f"Practitioner-practices:    {env['clinic.practitioner.practice'].search_count([])}")
print(f"Person links (incl mirrors): {env['clinic.person.link'].search_count([])}")
print(f"Coverages:                 {env['clinic.patient.coverage'].search_count([])}")
print(f"Appointments:              {env['clinic.appointment'].search_count([])}")
print("=" * 60)
