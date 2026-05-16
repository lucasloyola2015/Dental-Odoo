"""
Demo data loader for clinic_core (multi-sede version).

Run via Odoo shell:
    odoo-bin shell -c <odoo.conf> -d <db> --no-http < scripts/load_demo_data.py

Idempotent: deletes previous demo records (matched by DNI / medical_license / location code)
before creating fresh ones.

Layout V1 (post decision P):
- 2 sedes: ROL (Roldan Centro) y FUN (Funes).
- ROL trabaja con AOSS, FUN trabaja con ASOR.
- Dra. Tenaglia atiende en ROL y FUN.
- Dr. Soto solo en ROL.
- Dra. Cardozo solo en FUN.
"""

from datetime import date, datetime, time, timedelta

print("=" * 60)
print("Loading clinic demo data (multi-sede)...")
print("=" * 60)

main_company = env.company
print(f"Company: {main_company.name}")

# =============================================================================
# CLEANUP previous demo records
# =============================================================================
print("\n[1/8] Cleaning up previous demo data...")

# Match demo records by DNI (vat) so cleanup is robust regardless of HC format
demo_dnis = [
    "25123456", "30234567", "28345678", "32456789",
    "50678901", "48789012", "8890123", "10901234", "22567890",
]
demo_partners = env["res.partner"].with_context(active_test=False).search([
    ("vat", "in", demo_dnis),
])
demo_partner_ids = demo_partners.ids
demo_patients = env["clinic.patient"].with_context(active_test=False).search([
    ("partner_id", "in", demo_partner_ids),
])

if demo_partners:
    appts = env["clinic.appointment"].with_context(active_test=False).search([
        ("patient_id", "in", demo_patients.ids),
    ])
    print(f"  Deleting {len(appts)} appointments...")
    appts.unlink()

    coverages = env["clinic.patient.coverage"].with_context(active_test=False).search([
        "|", ("patient_id", "in", demo_patients.ids),
             ("holder_partner_id", "in", demo_partner_ids),
    ])
    print(f"  Deleting {len(coverages)} coverages...")
    coverages.unlink()

    links = env["clinic.person.link"].with_context(active_test=False).search([
        "|", ("partner_a_id", "in", demo_partner_ids),
             ("partner_b_id", "in", demo_partner_ids),
    ])
    print(f"  Deleting {len(links)} person links (mirrors cascade)...")
    links.unlink()

    print(f"  Deleting {len(demo_patients)} patients...")
    demo_patients.unlink()

    remaining = env["res.partner"].search([
        ("id", "in", demo_partner_ids),
    ])
    if remaining:
        print(f"  Deleting {len(remaining)} remaining demo partners...")
        remaining.unlink()

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

# Cleanup resource calendars (individual per practitioner-sede + legacy shared)
demo_calendars = env["resource.calendar"].with_context(active_test=False).search([
    "|", "|", "|",
    ("name", "in", [
        "Horario Clinica L-V 9-13/14-18 (demo)",
        "Horario ROL L-V 9-13/14-18 (demo)",
        "Horario FUN L-V 10-13/15-19 (demo)",
    ]),
    ("name", "=like", "Horario Tenaglia%(demo)"),
    ("name", "=like", "Horario Soto%(demo)"),
    ("name", "=like", "Horario Cardozo%(demo)"),
])
if demo_calendars:
    print(f"  Deleting {len(demo_calendars)} demo resource.calendars...")
    demo_calendars.unlink()

# Cleanup demo locations (by code) — also any orphaned roles/practices/appointments tied to them
demo_locations = env["clinic.location"].with_context(active_test=False).search([
    ("code", "in", ["ROL", "FUN"]),
])
if demo_locations:
    loc_partner_ids = demo_locations.mapped("partner_id").ids
    # Remove anything that still references these locations (FK violation otherwise)
    orphan_appts = env["clinic.appointment"].with_context(active_test=False).search([
        ("location_id", "in", demo_locations.ids),
    ])
    if orphan_appts:
        print(f"  Deleting {len(orphan_appts)} orphan appointments tied to demo locations...")
        orphan_appts.unlink()
    orphan_practices = env["clinic.practitioner.practice"].with_context(active_test=False).search([
        ("location_id", "in", demo_locations.ids),
    ])
    if orphan_practices:
        print(f"  Deleting {len(orphan_practices)} orphan practitioner-practices...")
        orphan_practices.unlink()
    orphan_roles = env["clinic.practitioner.role"].with_context(active_test=False).search([
        ("location_id", "in", demo_locations.ids),
    ])
    if orphan_roles:
        print(f"  Deleting {len(orphan_roles)} orphan practitioner-roles...")
        orphan_roles.unlink()
    print(f"  Deleting {len(demo_locations)} demo locations...")
    demo_locations.unlink()
    # Also clean their partners
    loc_partners = env["res.partner"].search([("id", "in", loc_partner_ids)])
    if loc_partners:
        loc_partners.unlink()

# =============================================================================
# LOCATIONS
# =============================================================================
print("\n[2/8] Creating sedes (locations)...")

route_aoss = env.ref("clinic_core.billing_route_aoss")
route_directo = env.ref("clinic_core.billing_route_directo")

# Try ASOR; if it doesn't exist as a billing_route, create it
route_asor = env["clinic.billing.route"].search([("code", "=", "ASOR")], limit=1)
if not route_asor:
    route_asor = env["clinic.billing.route"].create({
        "name": "ASOR (Asociacion de Odontologos de Rosario)",
        "code": "ASOR",
        "requires_membership": True,
        "observations": "Asociacion que nuclea las tarifas de odontologos del area Rosario.",
        "company_id": False,  # shared
    })
    print(f"  Created billing_route ASOR.")

location_rol = env["clinic.location"].create({
    "name": "Roldan Centro",
    "code": "ROL",
    "company_id": main_company.id,
    "billing_route_id": route_aoss.id,
    "sequence": 10,
    "notes": "Sede principal. Trabaja bajo AOSS (Asoc. Santa Fe 2da Circ.).",
})
# Address on its partner
location_rol.partner_id.write({
    "street": "Av. San Martin 1234",
    "city": "Roldan",
    "zip": "2134",
})

location_fun = env["clinic.location"].create({
    "name": "Funes",
    "code": "FUN",
    "company_id": main_company.id,
    "billing_route_id": route_asor.id,
    "sequence": 20,
    "notes": "Sede secundaria. Trabaja bajo ASOR (area Rosario).",
})
location_fun.partner_id.write({
    "street": "Av. Eva Peron 456",
    "city": "Funes",
    "zip": "2132",
})
print(f"  Created sedes: {location_rol.display_name} + {location_fun.display_name}")

# =============================================================================
# RESOURCE CALENDARS (one per sede)
# =============================================================================
print("\n[3/8] Creating resource.calendars per sede...")

def make_attendances(morning_from, morning_to, afternoon_from, afternoon_to):
    att = []
    for dow in range(5):  # Mon=0..Fri=4
        att.append((0, 0, {
            "name": "Manana",
            "dayofweek": str(dow),
            "hour_from": morning_from,
            "hour_to": morning_to,
            "day_period": "morning",
        }))
        att.append((0, 0, {
            "name": "Tarde",
            "dayofweek": str(dow),
            "hour_from": afternoon_from,
            "hour_to": afternoon_to,
            "day_period": "afternoon",
        }))
    return att

def make_calendar(name, attendance_tuple):
    return env["resource.calendar"].create({
        "name": name,
        "tz": "America/Argentina/Buenos_Aires",
        "attendance_ids": make_attendances(*attendance_tuple),
        "company_id": main_company.id,
    })

# One calendar per (practitioner, sede) so extras/leaves are individual
ROL_HOURS = (9.0, 13.0, 14.0, 18.0)
FUN_HOURS = (10.0, 13.0, 15.0, 19.0)

calendar_tenaglia_rol = make_calendar("Horario Tenaglia ROL (demo)", ROL_HOURS)
calendar_tenaglia_fun = make_calendar("Horario Tenaglia FUN (demo)", FUN_HOURS)
calendar_soto_rol = make_calendar("Horario Soto ROL (demo)", ROL_HOURS)
calendar_cardozo_fun = make_calendar("Horario Cardozo FUN (demo)", FUN_HOURS)
print(f"  Created 4 resource.calendars (uno por profesional-sede).")

# =============================================================================
# PRACTITIONERS
# =============================================================================
print("\n[4/8] Creating practitioners...")

spec_odonto = env.ref("clinic_core.specialty_odontologia")
spec_odonto_ped = env.ref("clinic_core.specialty_odontopediatria")
spec_endo = env.ref("clinic_core.specialty_endodoncia")
spec_orto = env.ref("clinic_core.specialty_ortodoncia")
spec_perio = env.ref("clinic_core.specialty_periodoncia")
spec_cirug = env.ref("clinic_core.specialty_cirugia_oral")

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
    "clinic_observations": "Atiende ninos y adultos. Trabaja en periodoncia con ficha completa. Atiende en Roldan y Funes.",
})

# Tenaglia trabaja en LAS DOS sedes — un role por sede
# En ROL trabaja con AOSS (la via de la sede), acepta todas las OS de AOSS.
role_tenaglia_rol = env["clinic.practitioner.role"].create({
    "employee_id": dra_tenaglia.id,
    "location_id": location_rol.id,
    "resource_calendar_id": calendar_tenaglia_rol.id,
    "assigned_route_id": location_rol.billing_route_id.id,
    "calendar_color": "#1f77b4",
})
# En FUN trabaja con ASOR aceptando todas sus OS. (Probar la exclusion manual desde la UI.)
role_tenaglia_fun = env["clinic.practitioner.role"].create({
    "employee_id": dra_tenaglia.id,
    "location_id": location_fun.id,
    "resource_calendar_id": calendar_tenaglia_fun.id,
    "assigned_route_id": location_fun.billing_route_id.id,
    "calendar_color": "#1f77b4",
})

dr_soto = env["hr.employee"].create({
    "name": "Dr. Martin Soto",
    "is_clinic_practitioner": True,
    "medical_license": "MP 67890 (SF)",
    "specialty_main_id": spec_endo.id,
    "specialty_ids": [(6, 0, [spec_endo.id, spec_odonto.id])],
    "default_appointment_duration_minutes": 60,
    "slots_buffer_post_minutes": 5,
    "work_email": "martin.soto@example.com",
    "clinic_observations": "Endodoncias bajo microscopio. 5 min de buffer entre turnos. Solo Roldan.",
})

# Soto solo en ROL — trabaja con AOSS aceptando todas las OS
role_soto_rol = env["clinic.practitioner.role"].create({
    "employee_id": dr_soto.id,
    "location_id": location_rol.id,
    "resource_calendar_id": calendar_soto_rol.id,
    "assigned_route_id": location_rol.billing_route_id.id,
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
    "clinic_observations": "Solo atiende en Funes.",
})

# Cardozo solo en FUN — trabaja con ASOR aceptando todas las OS
role_cardozo_fun = env["clinic.practitioner.role"].create({
    "employee_id": dra_cardozo.id,
    "location_id": location_fun.id,
    "resource_calendar_id": calendar_cardozo_fun.id,
    "assigned_route_id": location_fun.billing_route_id.id,
    "calendar_color": "#2ca02c",
})

print(f"  Created 3 practitioners with 4 sede-roles total.")

# =============================================================================
# PRACTITIONER-PRACTICES (precios por sede)
# =============================================================================
print("\n[5/8] Creating practitioner-practices per sede...")

# (employee, practice_xmlid, price, duration, location)
# Tenaglia atiende lo mismo en las dos sedes, pero algunos precios varian un poco
tenaglia_practices_rol = [
    ("practice_01_01", 30000, 30),
    ("practice_01_04", 35000, 30),
    ("practice_02_01", 50000, 45),
    ("practice_02_02", 70000, 60),
    ("practice_02_03", 95000, 75),
    ("practice_05_01", 40000, 30),
    ("practice_05_02", 20000, 15),
    ("practice_05_04", 30000, 30),
    ("practice_05_05", 22000, 15),
    ("practice_07_01", 35000, 30),
    ("practice_08_01", 40000, 45),
    ("practice_08_02", 80000, 60),
]
# En FUN cobra ~10% mas particular (zona mas cara)
tenaglia_practices_fun = [
    (p, int(price * 1.1), dur) for (p, price, dur) in tenaglia_practices_rol
]

soto_practices_rol = [
    ("practice_01_01", 35000, 30),
    ("practice_03_01", 110000, 60),
    ("practice_03_02", 170000, 75),
    ("practice_03_03", 195000, 90),
    ("practice_03_04", 230000, 90),
    ("practice_03_05", 80000, 45),
    ("practice_03_06", 70000, 45),
]

cardozo_practices_fun = [
    ("practice_01_01", 35000, 30),
    ("practice_09_02_05", 40000, 30),
    ("practice_09_02_07", 45000, 30),
    ("practice_10_01", 55000, 30),
    ("practice_10_06", 65000, 45),
    ("practice_10_09", 150000, 75),
]

practitioner_practices = (
    [(dra_tenaglia, p, price, dur, location_rol) for (p, price, dur) in tenaglia_practices_rol]
    + [(dra_tenaglia, p, price, dur, location_fun) for (p, price, dur) in tenaglia_practices_fun]
    + [(dr_soto, p, price, dur, location_rol) for (p, price, dur) in soto_practices_rol]
    + [(dra_cardozo, p, price, dur, location_fun) for (p, price, dur) in cardozo_practices_fun]
)

for emp, prac_xmlid, price, duration, loc in practitioner_practices:
    env["clinic.practitioner.practice"].create({
        "employee_id": emp.id,
        "practice_id": env.ref(f"clinic_core.{prac_xmlid}").id,
        "location_id": loc.id,
        "can_perform": True,
        "price_particular": price,
        "default_duration_minutes": duration,
    })
print(f"  Created {len(practitioner_practices)} practitioner-practice rows.")

# =============================================================================
# PATIENTS + Pedro (OSDE holder)
# =============================================================================
print("\n[6/8] Creating patients...")

pedro_patient = env["clinic.patient"].create({
    "name": "Pedro Mendez",
    "is_clinic_person": True,
    "birthdate": date(1975, 3, 15),
    "gender": "male",
    "vat": "22567890",
    "phone": "+5493455555555",
    "email": "pedro.mendez@example.com",
    "company_id": main_company.id,
    "secretariat_notes": "Titular de OSDE de sus hijos Sofia y Lucas.",
})
pedro = pedro_patient.partner_id
print(f"  Created Paciente (also OSDE holder): {pedro.name}")

carlos = env["clinic.patient"].create({
    "name": "Carlos Perez",
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
    "name": "Maria Lopez",
    "is_clinic_person": True,
    "birthdate": date(1985, 8, 22),
    "gender": "female",
    "vat": "30234567",
    "phone": "+5493422222222",
    "email": "maria.lopez@example.com",
    "company_id": main_company.id,
})

juan = env["clinic.patient"].create({
    "name": "Juan Garcia",
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

sofia = env["clinic.patient"].create({
    "name": "Sofia Mendez",
    "is_clinic_person": True,
    "birthdate": date(2018, 6, 1),
    "gender": "female",
    "vat": "50678901",
    "phone": "+5493411000001",
    "company_id": main_company.id,
    "secretariat_notes": "Menor. Comunicaciones al padre Pedro Mendez.",
})

lucas = env["clinic.patient"].create({
    "name": "Lucas Mendez",
    "is_clinic_person": True,
    "birthdate": date(2014, 4, 18),
    "gender": "male",
    "vat": "48789012",
    "phone": "+5493411000002",
    "company_id": main_company.id,
    "secretariat_notes": "Menor. Comunicaciones al padre Pedro Mendez.",
})

rosa = env["clinic.patient"].create({
    "name": "Dona Rosa Fernandez",
    "is_clinic_person": True,
    "birthdate": date(1948, 9, 12),
    "gender": "female",
    "vat": "8890123",
    "phone": "+5493466666666",
    "company_id": main_company.id,
    "secretariat_notes": "Jubilada. Atiende los martes preferentemente.",
})

roberto = env["clinic.patient"].create({
    "name": "Roberto Vazquez",
    "is_clinic_person": True,
    "birthdate": date(1955, 7, 3),
    "gender": "male",
    "vat": "10901234",
    "phone": "+5493477777777",
    "company_id": main_company.id,
})

patients_all = [carlos, maria, juan, ana, sofia, lucas, rosa, roberto]
print(f"  Created {len(patients_all)} patients.")

# Person links (Pedro → Sofia/Lucas)
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
sofia.write({"phone": False, "email": False, "use_external_contact": True})
lucas.write({"phone": False, "email": False, "use_external_contact": True})

# =============================================================================
# COVERAGES
# =============================================================================
print("\n[7/8] Creating coverages...")

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
# APPOINTMENTS (algunos en ROL, algunos en FUN)
# =============================================================================
print("\n[8/8] Creating appointments across both sedes...")

today = date.today()

def appt(patient, practitioner, practice_xmlid, start_dt, duration, state, location, **kw):
    practice = env.ref(f"clinic_core.{practice_xmlid}")
    coverage = patient.coverage_ids.filtered(lambda c: c.is_primary)[:1]
    vals = {
        "patient_id": patient.id,
        "practitioner_id": practitioner.id,
        "practice_id": practice.id,
        "start_datetime": start_dt,
        "duration_minutes": duration,
        "state": state,
        "location_id": location.id,
    }
    if coverage:
        vals["coverage_id"] = coverage.id
        vals["billing_route_id"] = location.billing_route_id.id
    else:
        vals["billing_route_id"] = route_directo.id
    vals.update(kw)
    return env["clinic.appointment"].create(vals)

today_dt = datetime.combine(today, time(9, 0))

# Hoy — mezclar sedes
appt(carlos, dra_tenaglia, "practice_05_01", today_dt.replace(hour=9, minute=0), 30, "fulfilled", location_rol,
     appointment_reason="Limpieza semestral. En Roldan.")
appt(maria, dra_tenaglia, "practice_02_01", today_dt.replace(hour=9, minute=30), 45, "fulfilled", location_rol,
     appointment_reason="Caries molar superior derecho.")
appt(juan, dr_soto, "practice_03_01", today_dt.replace(hour=10, minute=30), 60, "booked", location_rol,
     appointment_reason="Dolor en pieza 26, posible endodoncia.")
appt(sofia, dra_tenaglia, "practice_07_01", today_dt.replace(hour=11, minute=30), 30, "checked-in", location_rol,
     appointment_reason="Control general y motivacion.")
appt(ana, dra_tenaglia, "practice_05_01", today_dt.replace(hour=15, minute=0), 30, "pending", location_fun,
     appointment_reason="Profilaxis en sede Funes.")

# Manana
tmrw = today + timedelta(days=1)
appt(lucas, dra_tenaglia, "practice_05_02", datetime.combine(tmrw, time(10, 0)), 15, "booked", location_rol,
     appointment_reason="Fluor + control.")
appt(rosa, dra_tenaglia, "practice_08_01", datetime.combine(tmrw, time(10, 30)), 45, "booked", location_rol,
     appointment_reason="Sangrado de encias al cepillar.")
appt(roberto, dr_soto, "practice_03_02", datetime.combine(tmrw, time(14, 0)), 75, "pending", location_rol,
     appointment_reason="Tratamiento endodontico pieza 35.")

day_plus2 = today + timedelta(days=2)
appt(juan, dr_soto, "practice_03_01", datetime.combine(day_plus2, time(9, 0)), 60, "booked", location_rol,
     appointment_reason="Continuacion endodoncia.")
appt(maria, dra_cardozo, "practice_09_02_07", datetime.combine(day_plus2, time(11, 0)), 30, "pending", location_fun,
     appointment_reason="Estudio de ortodoncia en Funes.")

day_plus3 = today + timedelta(days=3)
appt(carlos, dra_tenaglia, "practice_02_02", datetime.combine(day_plus3, time(15, 0)), 60, "booked", location_rol,
     appointment_reason="Caries compuesta molar inferior.")

# Pasado
yesterday = today - timedelta(days=1)
appt(rosa, dra_tenaglia, "practice_01_01", datetime.combine(yesterday, time(10, 0)), 30, "fulfilled", location_rol,
     appointment_reason="Primera consulta.")
appt(ana, dra_tenaglia, "practice_05_01", datetime.combine(yesterday, time(11, 0)), 30, "fulfilled", location_fun)
appt(carlos, dra_tenaglia, "practice_05_01", datetime.combine(yesterday, time(15, 30)), 30, "cancelled", location_rol,
     cancellation_reason="Paciente aviso que no puede.")

days_ago_7 = today - timedelta(days=7)
appt(maria, dra_tenaglia, "practice_05_01", datetime.combine(days_ago_7, time(9, 0)), 30, "fulfilled", location_rol)
appt(juan, dra_tenaglia, "practice_01_01", datetime.combine(days_ago_7, time(10, 0)), 30, "fulfilled", location_rol)
appt(ana, dra_tenaglia, "practice_05_01", datetime.combine(days_ago_7, time(11, 0)), 30, "noshow", location_fun)
appt(lucas, dra_tenaglia, "practice_07_01", datetime.combine(days_ago_7, time(15, 0)), 30, "fulfilled", location_rol)

days_ago_14 = today - timedelta(days=14)
appt(carlos, dra_tenaglia, "practice_05_01", datetime.combine(days_ago_14, time(9, 0)), 30, "fulfilled", location_rol)
appt(roberto, dra_cardozo, "practice_10_01", datetime.combine(days_ago_14, time(15, 0)), 30, "fulfilled", location_fun)

days_ago_21 = today - timedelta(days=21)
appt(juan, dr_soto, "practice_03_02", datetime.combine(days_ago_21, time(10, 0)), 75, "noshow", location_rol)

print(f"  Created appointments across both sedes.")

# =============================================================================
# DIAS EXTRAS + VACACIONES (por profesional)
# =============================================================================
print("\n[9/9] Creating dias extras y vacaciones por profesional...")

import pytz
ar_tz = pytz.timezone("America/Argentina/Buenos_Aires")

def ar_to_utc_naive(d, h, m=0):
    """Combina date + hora local AR y devuelve datetime UTC naive para guardar en Odoo."""
    local = ar_tz.localize(datetime.combine(d, time(h, m)))
    return local.astimezone(pytz.UTC).replace(tzinfo=None)

# ------------- Tenaglia ROL -------------
# Extra: cubre la guardia un sabado en 14 dias, 10-13 hs (reemplazo Dr. Soto)
sat_14 = today + timedelta(days=(5 - today.weekday()) % 7 + 14)  # proximo sabado +14 dias
env["clinic.schedule.extra_day"].create({
    "calendar_id": calendar_tenaglia_rol.id,
    "date": sat_14,
    "hour_from": 10.0,
    "hour_to": 13.0,
    "name": "Reemplazo Dr. Soto (cirugias programadas)",
})
# Vacaciones: 2 semanas en 30 dias
vac_start = today + timedelta(days=30)
vac_end = vac_start + timedelta(days=14)
env["resource.calendar.leaves"].create({
    "calendar_id": calendar_tenaglia_rol.id,
    "name": "Vacaciones de verano",
    "date_from": ar_to_utc_naive(vac_start, 0, 0),
    "date_to": ar_to_utc_naive(vac_end, 23, 59),
    "time_type": "leave",
})

# ------------- Tenaglia FUN -------------
# Mismo bloque de vacaciones (es la misma persona) en su otro calendar
env["resource.calendar.leaves"].create({
    "calendar_id": calendar_tenaglia_fun.id,
    "name": "Vacaciones de verano",
    "date_from": ar_to_utc_naive(vac_start, 0, 0),
    "date_to": ar_to_utc_naive(vac_end, 23, 59),
    "time_type": "leave",
})
# Manana sin atencion (formacion clinica)
training_day = today + timedelta(days=21)
env["resource.calendar.leaves"].create({
    "calendar_id": calendar_tenaglia_fun.id,
    "name": "Curso de actualizacion en periodoncia (manana)",
    "date_from": ar_to_utc_naive(training_day, 10, 0),
    "date_to": ar_to_utc_naive(training_day, 13, 0),
    "time_type": "leave",
})

# ------------- Soto ROL -------------
# Extra: sabado en 7 dias para cirugias programadas
sat_7 = today + timedelta(days=(5 - today.weekday()) % 7 + 7)
env["clinic.schedule.extra_day"].create({
    "calendar_id": calendar_soto_rol.id,
    "date": sat_7,
    "hour_from": 9.0,
    "hour_to": 13.0,
    "name": "Cirugias programadas (con anestesia)",
})
# Extra: otro sabado en 28 dias, jornada doble (manana + tarde)
sat_28 = sat_7 + timedelta(days=21)
env["clinic.schedule.extra_day"].create({
    "calendar_id": calendar_soto_rol.id,
    "date": sat_28,
    "hour_from": 9.0,
    "hour_to": 17.0,
    "name": "Jornada doble por demanda acumulada",
})
# Vacaciones: 1 dia (cumpleanos) en 50 dias
birthday = today + timedelta(days=50)
env["resource.calendar.leaves"].create({
    "calendar_id": calendar_soto_rol.id,
    "name": "Cumpleanos",
    "date_from": ar_to_utc_naive(birthday, 0, 0),
    "date_to": ar_to_utc_naive(birthday, 23, 59),
    "time_type": "leave",
})

# ------------- Cardozo FUN -------------
# Extra: viernes en 21 dias, horario extendido 16-20 hs
fri_21 = today + timedelta(days=(4 - today.weekday()) % 7 + 21)
env["clinic.schedule.extra_day"].create({
    "calendar_id": calendar_cardozo_fun.id,
    "date": fri_21,
    "hour_from": 16.0,
    "hour_to": 20.0,
    "name": "Horario extendido para pacientes de ortodoncia",
})
# Vacaciones: 1 semana en 60 dias (congreso)
congress_start = today + timedelta(days=60)
congress_end = congress_start + timedelta(days=7)
env["resource.calendar.leaves"].create({
    "calendar_id": calendar_cardozo_fun.id,
    "name": "Congreso de ortodoncia en Buenos Aires",
    "date_from": ar_to_utc_naive(congress_start, 0, 0),
    "date_to": ar_to_utc_naive(congress_end, 23, 59),
    "time_type": "leave",
})

print(f"  Created extras + vacaciones for the 4 calendars.")

env.cr.commit()

print("\n" + "=" * 60)
print("DEMO DATA LOADED SUCCESSFULLY")
print("=" * 60)
print(f"Sedes:                     {env['clinic.location'].search_count([])}")
print(f"Patients:                  {env['clinic.patient'].search_count([])}")
print(f"Persons (res.partner):     {env['res.partner'].search_count([('is_clinic_person', '=', True)])}")
print(f"Practitioners:             {env['hr.employee'].search_count([('is_clinic_practitioner', '=', True)])}")
print(f"Practitioner-roles:        {env['clinic.practitioner.role'].search_count([])}")
print(f"Practitioner-practices:    {env['clinic.practitioner.practice'].search_count([])}")
print(f"Person links (incl mirrors): {env['clinic.person.link'].search_count([])}")
print(f"Coverages:                 {env['clinic.patient.coverage'].search_count([])}")
print(f"Appointments ROL:          {env['clinic.appointment'].search_count([('location_id', '=', env['clinic.location'].search([('code', '=', 'ROL')], limit=1).id)])}")
print(f"Appointments FUN:          {env['clinic.appointment'].search_count([('location_id', '=', env['clinic.location'].search([('code', '=', 'FUN')], limit=1).id)])}")
print(f"Total appointments:        {env['clinic.appointment'].search_count([])}")
print(f"Dias extras (demo):        {env['clinic.schedule.extra_day'].search_count([])}")
print(f"Vacaciones / leaves (demo): {env['resource.calendar.leaves'].search_count([('calendar_id.name', 'like', 'Horario')])}")
print("=" * 60)
