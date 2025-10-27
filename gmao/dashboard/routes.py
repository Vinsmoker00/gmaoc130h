from datetime import date, datetime

from flask import Blueprint, render_template
from flask_login import login_required

from ..models import Aircraft, MaintenanceTask, MaintenanceVisit, Material, PersonnelStatus

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

    return render_template(
        "dashboard.html",
        aircraft_total=aircraft_total,
        ongoing_visits=ongoing_visits,
        pending_tasks=pending_tasks,
        available_personnel=available_personnel,
        critical_materials=critical_materials,
        tasks_today=tasks_today,
    )


@bp.route("/home")
@login_required
def landing():
    return render_template("home.html")

