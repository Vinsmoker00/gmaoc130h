from datetime import date
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import url_for

from gmao import create_app
from gmao.config import TestingConfig
from gmao.extensions import db
from gmao.models import Aircraft, JobCard, MaintenanceVisit


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


def _login(client):
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_maintenance_delete_visit_endpoint_registered(app, client):
    aircraft = Aircraft(tail_number="C130-TEST")
    db.session.add(aircraft)
    visit = MaintenanceVisit(
        name="VP Test",
        aircraft=aircraft,
        vp_type="A",
        start_date=date.today(),
    )
    db.session.add(visit)
    db.session.commit()

    visit_id = visit.id

    with app.test_request_context():
        delete_url = url_for("maintenance.delete_visit", visit_id=visit_id)
        assert delete_url == f"/maintenance/{visit_id}/delete"

    _login(client)

    response = client.post(delete_url, follow_redirects=False)
    assert response.status_code == 302
    assert MaintenanceVisit.query.get(visit_id) is None


def test_archive_delete_card_endpoint_registered(app, client):
    card = JobCard(card_number="A-TEST", title="Test Card")
    db.session.add(card)
    db.session.commit()

    card_id = card.id

    with app.test_request_context():
        delete_url = url_for("archive.delete_card", card_id=card_id)
        assert delete_url == f"/archive/{card_id}/delete"

    _login(client)

    response = client.post(delete_url, follow_redirects=False)
    assert response.status_code == 302
    assert JobCard.query.get(card_id) is None
