import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gmao import create_app
from gmao.config import TestingConfig
from gmao.extensions import db
from gmao.maintenance.packages import package_for_visit
from gmao.models import (
    Aircraft,
    JobCard,
    JobCardMaterial,
    JobCardParagraph,
    JobCardStep,
    MaintenanceTask,
    MaintenanceVisit,
    Material,
)


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    app.config["WTF_CSRF_ENABLED"] = False
    ctx = app.app_context()
    ctx.push()
    yield app
    db.session.remove()
    db.drop_all()
    ctx.pop()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    return response


def test_visit_creation_populates_package_tasks(client):
    login(client)
    aircraft = Aircraft(tail_number="C130-TEST")
    material = Material(designation="Filtre", category="REPARABLE")
    job_card = JobCard(card_number="A-16", title="Inspection générale")
    paragraph = JobCardParagraph(job_card=job_card, title="Préparation", order_index=1, estimated_minutes=30)
    step = JobCardStep(
        job_card=job_card,
        paragraph=paragraph,
        description="Inspecter la zone d'accès",
        order_index=1,
        estimated_minutes=30,
    )
    job_material = JobCardMaterial(job_card=job_card, material=material, step=step, quantity=2)
    db.session.add_all([aircraft, material, job_card, paragraph, step, job_material])
    db.session.commit()

    response = client.post(
        "/maintenance/create",
        data={
            "name": "Visite A",
            "aircraft_id": aircraft.id,
            "vp_type": "A",
            "start_date": "2024-01-01",
            "end_date": "2024-01-15",
            "status": "planned",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    visit = MaintenanceVisit.query.filter_by(name="Visite A").first()
    assert visit is not None
    tasks = MaintenanceTask.query.filter_by(visit_id=visit.id).all()
    assert len(tasks) == len(package_for_visit("A"))

    a16_task = MaintenanceTask.query.filter_by(visit_id=visit.id, package_code="A-16").first()
    assert a16_task is not None
    assert a16_task.job_card_id == job_card.id
    assert a16_task.is_package_item is True
    assert pytest.approx(a16_task.estimated_hours, 0.01) == pytest.approx(job_card.estimated_hours, 0.01)

    detail_page = client.get(f"/maintenance/{visit.id}")
    html = detail_page.get_data(as_text=True)
    assert "Synthèse matériel" in html
    assert "Filtre" in html


def test_package_sync_attaches_new_job_card(client):
    login(client)
    aircraft = Aircraft(tail_number="C130-SYNC")
    db.session.add(aircraft)
    db.session.commit()

    response = client.post(
        "/maintenance/create",
        data={
            "name": "Visite sans archive",
            "aircraft_id": aircraft.id,
            "vp_type": "A",
            "start_date": "2024-02-01",
            "status": "planned",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    visit = MaintenanceVisit.query.filter_by(name="Visite sans archive").first()
    assert visit is not None
    placeholder = MaintenanceTask.query.filter_by(visit_id=visit.id, package_code="A-16").first()
    assert placeholder is not None
    assert placeholder.job_card_id is None

    job_card = JobCard(card_number="A-16", title="Inspection requalifiée")
    db.session.add(job_card)
    db.session.commit()

    sync_response = client.post(
        f"/maintenance/{visit.id}/package/sync",
        follow_redirects=True,
    )
    assert sync_response.status_code == 200

    updated = MaintenanceTask.query.filter_by(visit_id=visit.id, package_code="A-16").first()
    assert updated is not None
    assert updated.job_card_id == job_card.id
    assert updated.name.startswith("A-16")
