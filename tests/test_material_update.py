from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gmao import create_app
from gmao.config import TestingConfig
from gmao.extensions import db
from gmao.models import Aircraft, Material, MaterialSerial, Workshop


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
    return client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )


def test_material_identifier_updates(client):
    login_response = login(client)
    assert login_response.status_code == 200

    material = Material(designation="Test Item", category="TEST")
    db.session.add(material)
    db.session.commit()
    material_id = material.id

    response = client.post(
        f"/materials/{material_id}/update",
        data={
            "nsn": "1234-00-123-4567",
            "niin": "00-123-4567",
            "fsc": "1234",
            "cage_code": "1A234",
            "da_reference": "DA-2024-00123",
            "da_status": "En cours",
            "contract_type": "FMS",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "value=\"1234-00-123-4567\"" in page
    assert "value=\"00-123-4567\"" in page
    assert "value=\"1234\"" in page
    assert "value=\"1A234\"" in page
    assert "value=\"DA-2024-00123\"" in page
    assert "value=\"En cours\"" in page
    assert "value=\"FMS\"" in page

    updated = Material.query.get(material_id)
    assert updated.nsn == "1234-00-123-4567"
    assert updated.niin == "00-123-4567"
    assert updated.fsc == "1234"
    assert updated.cage_code == "1A234"
    assert updated.da_reference == "DA-2024-00123"
    assert updated.da_status == "En cours"
    assert updated.contract_type == "FMS"

    response = client.post(
        f"/materials/{material_id}/update",
        data={
            "nsn": " ",
            "niin": "",
            "fsc": "",
            "cage_code": "",
            "da_reference": "",
            "da_status": "",
            "contract_type": " ",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "value=\"1234-00-123-4567\"" not in page
    assert "value=\"00-123-4567\"" not in page
    assert "value=\"1A234\"" not in page
    assert "value=\"DA-2024-00123\"" not in page

    cleared = Material.query.get(material_id)
    assert cleared.nsn is None
    assert cleared.niin is None
    assert cleared.fsc is None
    assert cleared.cage_code is None
    assert cleared.da_reference is None
    assert cleared.da_status is None
    assert cleared.contract_type is None


def test_reparable_creation_with_serials(client):
    login_response = login(client)
    assert login_response.status_code == 200

    workshop = Workshop(name="Essais", description="Atelier d'essais")
    aircraft = Aircraft(tail_number="C130-001")
    db.session.add_all([workshop, aircraft])
    db.session.commit()

    response = client.post(
        "/materials/create",
        data={
            "designation": "Valves de régulation",
            "category": "reparable",
            "workshop_id": str(workshop.id),
            "dotation": "2",
            "per_aircraft": "2",
            "annual_consumption": "4",
            "serials-0-serial_number": "VALVE-001",
            "serials-0-status": "avionnee",
            "serials-0-aircraft_id": str(aircraft.id),
            "serials-0-under_warranty": "on",
            "serials-1-serial_number": "VALVE-002",
            "serials-1-status": "att_rpn",
            "serials-1-da_reference": "DA-0001",
            "serials-1-da_status": "En transit",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    material = Material.query.filter_by(designation="Valves de régulation").first()
    assert material is not None
    assert material.category == "reparable"
    assert material.dotation == 2
    assert material.avionnee == 1
    assert material.unavailable_for_repair == 1
    assert material.in_repair == 0
    assert material.primary_workshop == workshop

    serials = MaterialSerial.query.filter_by(material_id=material.id).order_by(MaterialSerial.serial_number).all()
    assert len(serials) == 2
    assert serials[0].serial_number == "VALVE-001"
    assert serials[0].status == "avionnee"
    assert serials[0].aircraft_id == aircraft.id
    assert serials[0].under_warranty is True

    assert serials[1].serial_number == "VALVE-002"
    assert serials[1].status == "att_rpn"
    assert serials[1].da_reference == "DA-0001"
    assert serials[1].da_status == "En transit"

    issues = material.serial_data_issues()
    assert issues == []
