from __future__ import annotations

from datetime import date, timedelta

from flask import current_app

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


def register_seed_commands(app):
    @app.cli.command("seed-demo")
    def seed_demo():
        """Populate the database with a representative demo dataset."""

        db.drop_all()
        db.create_all()
        current_app.logger.info("Seeding demo data ...")

        admin_role = Role(name="admin", description="Full access")
        engineer_role = Role(name="engineer", description="Engineering management")
        technician_role = Role(name="technician", description="Workshop technician")

        db.session.add_all([admin_role, engineer_role, technician_role])

        workshops = {
            name: Workshop(name=name)
            for name in [
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
        }
        db.session.add_all(workshops.values())

        admin = User(username="admin", full_name="Admin GMAO", rank="CPT", role=admin_role)
        admin.set_password("admin123")
        db.session.add(admin)

        engineers = []
        for idx in range(1, 4):
            engineer = User(
                username=f"eng{idx}",
                full_name=f"Engineer {idx}",
                rank="ING",
                role=engineer_role,
            )
            engineer.set_password("password")
            db.session.add(engineer)
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

        db.session.flush()

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
            aircraft_list.append(aircraft)

        materials = []
        for record in MATERIAL_DATA:
            designation = record["Designation"]
            category = "hydraulique" if "VALVE" in designation else "instrumentation"
            material = Material(
                designation=designation,
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
                contract_type="cadre" if "REG" in record["PN"] else "ferme",
                per_aircraft=1,
                annual_consumption=int(record["consommation annuelle"] or 0),
                da_reference=record["DA"],
                da_status=record["status DA"],
            )
            materials.append(material)
            db.session.add(material)

        db.session.flush()

        for material in materials:
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

        db.session.flush()

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

        db.session.flush()

        for material in materials:
            prediction = DemandPrediction(
                material=material,
                window_days=30,
                predicted_need=max(material.annual_consumption / 12, 1),
                model="wilson",
            )
            db.session.add(prediction)

        db.session.commit()
        current_app.logger.info("Demo data seeded successfully")
