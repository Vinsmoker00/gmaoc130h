from pathlib import Path
import sys

import pytest
from flask import template_rendered

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gmao import create_app
from gmao.config import TestingConfig
from gmao.extensions import db


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


@pytest.fixture
def captured_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


def _get_dashboard_context(recorded):
    for template, context in recorded:
        if template.name == "dashboard.html":
            return context
    raise AssertionError("dashboard.html was not rendered")


def test_dashboard_includes_chart_datasets(client, captured_templates):
    login_response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    assert login_response.status_code == 200

    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200

    context = _get_dashboard_context(captured_templates)

    task_chart = context.get("task_status_chart")
    assert task_chart is not None
    assert isinstance(task_chart.get("labels"), list)
    assert isinstance(task_chart.get("datasets"), list)

    visit_chart = context.get("visit_progress_chart")
    assert visit_chart is not None
    assert len(visit_chart.get("labels", [])) == 6
    datasets = visit_chart.get("datasets", [])
    assert len(datasets) == 2
    for dataset in datasets:
        assert len(dataset.get("data", [])) == 6

    material_chart = context.get("material_shortages_chart")
    assert material_chart is not None
    assert isinstance(material_chart.get("labels"), list)
    material_datasets = material_chart.get("datasets", [])
    assert len(material_datasets) == 2
    for dataset in material_datasets:
        assert len(dataset.get("data", [])) == len(material_chart.get("labels"))
