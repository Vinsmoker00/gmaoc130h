from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gmao import create_app
from gmao.config import TestingConfig
from gmao.extensions import db
from gmao.models import Material


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
