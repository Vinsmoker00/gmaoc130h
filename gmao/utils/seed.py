from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, Iterable, List

from flask import current_app
from werkzeug.security import generate_password_hash

from ..extensions import db
from ..models import (
    Aircraft,
    DemandPrediction,
    InventorySnapshot,
    JobCard,
    Material,
    MaintenanceTask,
    MaintenanceVisit,
    MaterialRequirement,
    PersonnelStatus,
    Role,
    User,
    Workshop,
)
from .demo_data import AIRCRAFT_DATA, MATERIAL_DATA, PERSONNEL_DATA, generate_visit_schedule

WORKSHOP_NAMES: List[str] = [
    "MOTEUR",
    "EQT/BORD",
    "RADIO",
    "APG",
    "HELICE",
    "FUEL",
    "CHAUD",
    "MARS",
    "S/S",
    "DRS",
    "NDI",
]

ADMIN_PASSWORD_HASH = generate_password_hash("admin123")
DEFAULT_USER_PASSWORD_HASH = generate_password_hash("password")


def register_seed_commands(app):
    @app.cli.command("seed-demo")
    def seed_demo():
        """Populate the database with a representative demo dataset."""

        current_app.logger.info("Resetting database before demo seed ...")
        was_seeded = populate_demo_data(reset=True, skip_if_exists=False)
        if was_seeded:
            current_app.logger.info("Demo data seeded successfully")
        else:
            current_app.logger.info("Demo data already present; skipped seeding")


def populate_demo_data(reset: bool = False, skip_if_exists: bool = True) -> bool:
    """Populate the database with curated demo data.

    Args:
        reset: When True the schema is dropped and recreated before loading data.
        skip_if_exists: When True the function will return immediately if demo
            records are already present.

    Returns:
        bool: True if the demo data was inserted during this invocation.
    """

    if reset:
        db.drop_all()
        db.create_all()

    if skip_if_exists and _demo_records_exist():
        return False

    roles = _ensure_roles()
    workshops = _ensure_workshops()
    admin_user = _ensure_admin_user(roles)
    engineers = _ensure_engineers(roles)
    technicians = _ensure_technicians(roles, workshops)

    _ensure_personnel_statuses(technicians)
    aircraft = _ensure_aircraft()
    materials = _ensure_materials()
    _ensure_inventory_snapshots(materials)

    visits_created = False
    if MaintenanceVisit.query.count() == 0:
        visits = _create_visits(aircraft)
        visits_created = True
    else:
        visits = MaintenanceVisit.query.order_by(MaintenanceVisit.start_date).all()

    if visits_created and MaintenanceTask.query.count() == 0:
        _create_tasks(visits, technicians, materials, workshops)

    if JobCard.query.count() == 0:
        _create_job_cards()

    if DemandPrediction.query.count() == 0:
        _create_demand_predictions(materials)

    db.session.commit()

    current_app.logger.debug(
        "Demo seed complete: %s admin=%s engineers=%d technicians=%d aircraft=%d materials=%d",
        "reset" if reset else "initial", admin_user.username, len(engineers), len(technicians), len(aircraft), len(materials)
    )
    return True


def _demo_records_exist() -> bool:
    return any(
        model.query.count() > 0
        for model in (
            Aircraft,
            Material,
            MaintenanceVisit,
            PersonnelStatus,
        )
    )


def _ensure_roles() -> Dict[str, Role]:
    definitions = {
        "admin": "Full access",
        "engineer": "Engineering management",
        "technician": "Workshop technician",
    }
    roles: Dict[str, Role] = {}
    for name, description in definitions.items():
        role = Role.query.filter_by(name=name).first()
        if role is None:
            role = Role(name=name, description=description)
            db.session.add(role)
        roles[name] = role
    db.session.flush()
    return roles


def _ensure_workshops() -> Dict[str, Workshop]:
    workshops: Dict[str, Workshop] = {}
    for name in WORKSHOP_NAMES:
        workshop = Workshop.query.filter_by(name=name).first()
        if workshop is None:
            workshop = Workshop(name=name)
            db.session.add(workshop)
        workshops[name] = workshop
    db.session.flush()
    return workshops


def _ensure_admin_user(roles: Dict[str, Role]) -> User:
    admin = User.query.filter_by(username="admin").first()
    if admin is None:
        admin = User(
            username="admin",
            full_name="Admin GMAO",
            rank="CPT",
            role=roles["admin"],
        )
        admin.password_hash = ADMIN_PASSWORD_HASH
        db.session.add(admin)
        db.session.flush()
    return admin


def _ensure_engineers(roles: Dict[str, Role]) -> List[User]:
    engineers: List[User] = []
    for idx in range(1, 4):
        username = f"eng{idx}"
        engineer = User.query.filter_by(username=username).first()
        if engineer is None:
            engineer = User(
                username=username,
                full_name=f"Engineer {idx}",
                rank="ING",
                role=roles["engineer"],
            )
            engineer.password_hash = DEFAULT_USER_PASSWORD_HASH
            db.session.add(engineer)
            db.session.flush()
        engineers.append(engineer)
    return engineers


def _ensure_technicians(roles: Dict[str, Role], workshops: Dict[str, Workshop]) -> List[User]:
    technicians: List[User] = []
    for record in PERSONNEL_DATA:
        username = record["Matricule"].lower()
        technician = User.query.filter_by(username=username).first()
        if technician is None:
            technician = User(
                username=username,
                full_name=f"{record['Prénom']} {record['Nom']}",
                rank=record["Grade"],
                role=roles["technician"],
                workshop=workshops.get(record["Atelier"]),
            )
            technician.password_hash = DEFAULT_USER_PASSWORD_HASH
            db.session.add(technician)
            db.session.flush()
        technicians.append(technician)
    return technicians
            engineers.append(engineer)

        technicians = []
        for record in PERSONNEL_DATA:
            workshop = workshops.get(record["Atelier"])
            user = User(
                username=record["Matricule"].lower(),
                full_name=f"{record['Prénom']} {record['Nom']}",
                rank=record["Grade"],
                role=technician_role,
                workshop=workshop,
            )
            user.set_password("password")
            db.session.add(user)
            technicians.append(user)


def _ensure_personnel_statuses(technicians: Iterable[User]) -> None:
    existing = {status.personnel_id for status in PersonnelStatus.query.all()}
    record_map = {record["Matricule"].lower(): record for record in PERSONNEL_DATA}

    status_duration = {
        "repos": 2,
        "congé": 10,
        "malade": 7,
        "permanence": None,
        "perma": None,
        "en site": None,
        "autres": None,
    }

    for idx, technician in enumerate(technicians):
        if technician.id in existing:
            continue
        record = record_map[technician.username]
        status_label = record["Status"]
        start_offset = idx % 21
        start = date.today() - timedelta(days=start_offset)
        duration = status_duration.get(status_label)
        end = start + timedelta(days=duration) if duration else None
        status = PersonnelStatus(
            personnel=technician,
            status=status_label,
            details=f"Situation familiale: {record['Situation Familiale']}",
            start_date=start,
            end_date=end,
        )
        db.session.add(status)


def _ensure_aircraft() -> List[Aircraft]:
    aircraft_objects: List[Aircraft] = []
    for record in AIRCRAFT_DATA:
        tail_number = record["Matricule"]
        aircraft = Aircraft.query.filter_by(tail_number=tail_number).first()
        if aircraft is None:
            aircraft = Aircraft(
                tail_number=tail_number,
        status_duration = {
            "repos": 2,
            "congé": 10,
            "malade": 7,
            "permanence": None,
            "perma": None,
            "en site": None,
            "autres": None,
        }

        for idx, technician in enumerate(technicians):
            record = PERSONNEL_DATA[idx]
            status_label = record["Status"]
            start_offset = idx % 21
            start = date.today() - timedelta(days=start_offset)
            duration = status_duration.get(status_label)
            end = start + timedelta(days=duration) if duration else None
            status = PersonnelStatus(
                personnel=technician,
                status=status_label,
                details=f"Situation familiale: {record['Situation Familiale']}",
                start_date=start,
                end_date=end,
            )
            db.session.add(status)

        aircraft_list = []
        for record in AIRCRAFT_DATA:
            aircraft = Aircraft(
                tail_number=record["Matricule"],
                aircraft_type=record["Type"],
                location=record["Position"],
                status=record["Statut"],
                notes="Flotte RMAF C-130H",
            )
            db.session.add(aircraft)
            db.session.flush()
        aircraft_objects.append(aircraft)
    return aircraft_objects


def _ensure_materials() -> List[Material]:
    materials: List[Material] = []
    for record in MATERIAL_DATA:
        part_number = record["PN"]
        serial = record["SN"]
        material = Material.query.filter_by(part_number=part_number, serial_number=serial).first()
        if material is None:
        materials = []
        for record in MATERIAL_DATA:
            designation = record["Designation"]
            category = "hydraulique" if "VALVE" in designation else "instrumentation"
            material = Material(
                designation=designation,
                part_number=part_number,
                serial_number=serial,
                part_number=record["PN"],
                serial_number=record["SN"],
                category=category,
                dotation=int(record["dotation"] or 0),
                avionnee=int(record["avionne"] or 0),
                stock=int(record["stock"] or 0),
                unavailable_for_repair=int(record["indispo att rpn"] or 0),
                in_repair=int(record["en rpn"] or 0),
                litigation=int(record["litige"] or 0),
                scrapped=int(record["reforme"] or 0),
                warranty=False,
                contract_type="cadre" if "REG" in part_number else "ferme",
                contract_type="cadre" if "REG" in record["PN"] else "ferme",
                per_aircraft=1,
                annual_consumption=int(record["consommation annuelle"] or 0),
                da_reference=record["DA"],
                da_status=record["status DA"],
            )
            db.session.add(material)
            db.session.flush()
        materials.append(material)
    return materials


def _ensure_inventory_snapshots(materials: Iterable[Material]) -> None:
    for material in materials:
        snapshot = InventorySnapshot.query.filter_by(material_id=material.id).first()
        if snapshot is None:
            snapshot = InventorySnapshot(
                material=material,
                available=material.stock,
                reserved=max(material.avionnee - material.stock, 0),
                consumption_window_days=30,
            )
            db.session.add(snapshot)

        visits = []
        visit_records = generate_visit_schedule(100)
        aircraft_by_tail = {aircraft.tail_number: aircraft for aircraft in aircraft_list}
        for record in visit_records:
            aircraft = aircraft_by_tail[record["aircraft"]]
            visit = MaintenanceVisit(
                name=record["name"],
                aircraft=aircraft,
                vp_type=record["vp_type"],
                status=record["status"],
                start_date=record["start_date"],
                end_date=record["end_date"],
                description=f"Programme {record['vp_type']} de la flotte RMAF",
            )
            db.session.add(visit)
            visits.append(visit)

def _create_visits(aircraft: List[Aircraft]) -> List[MaintenanceVisit]:
    visit_records = generate_visit_schedule(100)
    aircraft_by_tail = {item.tail_number: item for item in aircraft}
    visits: List[MaintenanceVisit] = []
    for record in visit_records:
        aircraft_obj = aircraft_by_tail[record["aircraft"]]
        visit = MaintenanceVisit(
            name=record["name"],
            aircraft=aircraft_obj,
            vp_type=record["vp_type"],
            status=record["status"],
            start_date=record["start_date"],
            end_date=record["end_date"],
            description=f"Programme {record['vp_type']} de la flotte RMAF",
        )
        db.session.add(visit)
        visits.append(visit)
    db.session.flush()
    return visits

        task_templates = [
            ("Inspection structure", "pending"),
            ("Tests moteurs", "in_progress"),
            ("Validation documentation", "completed"),
        ]
        workshop_cycle = list(workshops.values())

        for visit_idx, visit in enumerate(visits):
            for task_idx, (task_name, base_status) in enumerate(task_templates):
                task_status = base_status
                if visit.status == "ongoing" and task_idx == 0:
                    task_status = "ongoing"
                task = MaintenanceTask(
                    visit=visit,
                    workshop=workshop_cycle[(visit_idx + task_idx) % len(workshop_cycle)],
                    lead=technicians[(visit_idx + task_idx) % len(technicians)],
                    name=f"{task_name} {visit.vp_type}",
                    status=task_status,
                    estimated_hours=6 + task_idx * 3,
                )
                db.session.add(task)

                for requirement_idx in range(2):
                    material = materials[(visit_idx + requirement_idx + task_idx) % len(materials)]
                    requirement = MaterialRequirement(
                        task=task,
                        material=material,
                        quantity=1 + (task_idx + requirement_idx) % 3,
                        fulfilled=task_status == "completed",
                    )
                    db.session.add(requirement)

        for idx in range(1, 11):
            job_card = JobCard(
                card_number=f"JC-{idx:04d}",
                title=f"Maintenance Card {idx}",
                revision="A",
                summary="Standard maintenance procedure",
                content="Detailed steps for the maintenance activity.",
            )
            db.session.add(job_card)

def _create_tasks(
    visits: List[MaintenanceVisit],
    technicians: List[User],
    materials: List[Material],
    workshops: Dict[str, Workshop],
) -> None:
    task_templates = [
        ("Inspection structure", "pending"),
        ("Tests moteurs", "in_progress"),
        ("Validation documentation", "completed"),
    ]
    workshop_cycle = list(workshops.values())

    for visit_idx, visit in enumerate(visits):
        for task_idx, (task_name, base_status) in enumerate(task_templates):
            task_status = base_status
            if visit.status == "ongoing" and task_idx == 0:
                task_status = "ongoing"
            task = MaintenanceTask(
                visit=visit,
                workshop=workshop_cycle[(visit_idx + task_idx) % len(workshop_cycle)],
                lead=technicians[(visit_idx + task_idx) % len(technicians)],
                name=f"{task_name} {visit.vp_type}",
                status=task_status,
                estimated_hours=6 + task_idx * 3,
            )
            db.session.add(task)

            for requirement_idx in range(2):
                material = materials[(visit_idx + requirement_idx + task_idx) % len(materials)]
                requirement = MaterialRequirement(
                    task=task,
                    material=material,
                    quantity=1 + (task_idx + requirement_idx) % 3,
                    fulfilled=task_status == "completed",
                )
                db.session.add(requirement)


def _create_job_cards() -> None:
    for idx in range(1, 11):
        job_card = JobCard(
            card_number=f"JC-{idx:04d}",
            title=f"Maintenance Card {idx}",
            revision="A",
            summary="Standard maintenance procedure",
            content="Detailed steps for the maintenance activity.",
        )
        db.session.add(job_card)


def _create_demand_predictions(materials: Iterable[Material]) -> None:
    for material in materials:
        prediction = DemandPrediction(
            material=material,
            window_days=30,
            predicted_need=max(material.annual_consumption / 12, 1),
            model="wilson",
        )
        db.session.add(prediction)
