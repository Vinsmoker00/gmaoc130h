from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func
from dateutil.relativedelta import relativedelta

from ..models import Aircraft, MaintenanceTask, MaintenanceVisit, Material, PersonnelStatus
from ..extensions import db

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def home():
    aircraft_total = Aircraft.query.count()
    ongoing_visits = MaintenanceVisit.query.filter(MaintenanceVisit.status == "ongoing").all()
    pending_tasks = MaintenanceTask.query.filter(MaintenanceTask.status != "completed").count()
    available_personnel = PersonnelStatus.query.filter(PersonnelStatus.status == "on-site").count()
    critical_materials = Material.query.filter(Material.stock < Material.dotation).limit(5).all()
    today = datetime.combine(date.today(), datetime.min.time())
    tasks_today = (
        MaintenanceTask.query.filter(MaintenanceTask.started_at != None)
        .filter(MaintenanceTask.started_at >= today)
        .count()
    )

    task_status_chart = _build_task_status_chart()
    visit_progress_chart = _build_visit_progress_chart()
    material_shortages_chart = _build_material_shortages_chart()

    return render_template(
        "dashboard.html",
        aircraft_total=aircraft_total,
        ongoing_visits=ongoing_visits,
        pending_tasks=pending_tasks,
        available_personnel=available_personnel,
        critical_materials=critical_materials,
        tasks_today=tasks_today,
        task_status_chart=task_status_chart,
        visit_progress_chart=visit_progress_chart,
        material_shortages_chart=material_shortages_chart,
    )


@bp.route("/home")
@login_required
def landing():
    return render_template("home.html")


def _build_task_status_chart() -> Dict[str, List]:
    status_counts = (
        db.session.query(MaintenanceTask.status, func.count(MaintenanceTask.id))
        .group_by(MaintenanceTask.status)
        .all()
    )
    labels: List[str] = []
    data: List[int] = []
    for status, count in sorted(status_counts, key=lambda item: item[0] or ""):
        labels.append(status or "Non défini")
        data.append(count)

    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Répartition des tâches",
                "data": data,
            }
        ],
    }


def _build_visit_progress_chart() -> Dict[str, List]:
    started_counts: Dict[str, int] = defaultdict(int)
    completed_counts: Dict[str, int] = defaultdict(int)

    for visit in MaintenanceVisit.query.all():
        if visit.start_date is not None:
            key = visit.start_date.replace(day=1).strftime("%Y-%m")
            started_counts[key] += 1
        if visit.end_date is not None:
            key = visit.end_date.replace(day=1).strftime("%Y-%m")
            completed_counts[key] += 1

    month_labels: List[str] = []
    month_keys: List[str] = []
    current_month = date.today().replace(day=1)
    for offset in range(5, -1, -1):
        month = current_month - relativedelta(months=offset)
        month_keys.append(month.strftime("%Y-%m"))
        month_labels.append(month.strftime("%m/%Y"))

    started_series = [started_counts.get(key, 0) for key in month_keys]
    completed_series = [completed_counts.get(key, 0) for key in month_keys]

    return {
        "labels": month_labels,
        "datasets": [
            {
                "label": "Visites démarrées",
                "data": started_series,
            },
            {
                "label": "Visites clôturées",
                "data": completed_series,
            },
        ],
    }


def _build_material_shortages_chart() -> Dict[str, List]:
    shortage_materials = (
        Material.query.filter(Material.dotation > Material.stock)
        .order_by((Material.dotation - Material.stock).desc())
        .limit(7)
        .all()
    )

    labels = [material.designation for material in shortage_materials]
    dotations = [material.dotation for material in shortage_materials]
    stocks = [material.stock for material in shortage_materials]

    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Dotation",
                "data": dotations,
            },
            {
                "label": "Stock",
                "data": stocks,
            },
        ],
    }

