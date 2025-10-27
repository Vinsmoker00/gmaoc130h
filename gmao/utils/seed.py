from __future__ import annotations

from datetime import date, timedelta
from random import choice, randint

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
        for idx in range(1, 11):
            workshop = choice(list(workshops.values()))
            tech = User(
                username=f"tech{idx}",
                full_name=f"Technician {idx}",
                rank="SGT",
                role=technician_role,
                workshop=workshop,
            )
            tech.set_password("password")
            db.session.add(tech)
            technicians.append(tech)

        db.session.flush()

        aircraft_list = []
        for idx in range(1, 16):
            aircraft = Aircraft(
                tail_number=f"C130-{idx:02d}",
                location=choice(["BASE A", "BASE B", "BASE C"]),
                status=choice(["available", "in maintenance", "awaiting inspection"]),
            )
            db.session.add(aircraft)
            aircraft_list.append(aircraft)

        materials = []
        categories = ["reparable", "consommable", "outillage", "banc d'essai"]
        for idx in range(1, 51):
            category = choice(categories)
            material = Material(
                designation=f"Component {idx}",
                part_number=f"PN-{idx:04d}",
                serial_number=f"SN-{idx:05d}",
                category=category,
                dotation=randint(1, 5),
                avionnee=randint(0, 4),
                stock=randint(0, 10),
                unavailable_for_repair=randint(0, 3),
                in_repair=randint(0, 3),
                litigation=randint(0, 1),
                scrapped=randint(0, 1),
                warranty=choice([True, False]),
                contract_type=choice(["cadre", "ferme", ""],),
                per_aircraft=randint(1, 4),
                annual_consumption=randint(5, 40),
                da_reference=f"DA-{idx:04d}",
                da_status=choice(["en cours", "livre", "en retard"]),
                consumable_stock=randint(0, 30),
                consumable_dotation=randint(0, 10),
                consumable_type=choice(["RCA", "RCB", ""]),
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
        for idx in range(1, 6):
            aircraft = choice(aircraft_list)
            start = date.today() - timedelta(days=idx * 7)
            visit = MaintenanceVisit(
                name=f"VP-{idx:02d}",
                aircraft=aircraft,
                vp_type=choice(["A", "B", "C", "D"]),
                status=choice(["planned", "ongoing", "completed"]),
                start_date=start,
                end_date=start + timedelta(days=randint(7, 21)),
                description="Periodic maintenance visit",
            )
            db.session.add(visit)
            visits.append(visit)

        db.session.flush()

        for visit in visits:
            for idx in range(1, 6):
                task = MaintenanceTask(
                    visit=visit,
                    workshop=choice(list(workshops.values())),
                    lead=choice(technicians),
                    name=f"Task {visit.name}-{idx}",
                    status=choice(["pending", "in_progress", "completed"]),
                    estimated_hours=randint(2, 12),
                )
                db.session.add(task)
                for _ in range(2):
                    requirement = MaterialRequirement(
                        task=task,
                        material=choice(materials),
                        quantity=randint(1, 3),
                        fulfilled=choice([True, False]),
                    )
                    db.session.add(requirement)

        for tech in technicians:
            status = PersonnelStatus(
                personnel=tech,
                status=choice(["on-site", "day-off", "holidays", "sick"]),
                start_date=date.today() - timedelta(days=randint(0, 3)),
                end_date=date.today() + timedelta(days=randint(0, 3)),
            )
            db.session.add(status)

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
