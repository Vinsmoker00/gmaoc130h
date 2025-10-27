from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models import (
    Aircraft,
    MaintenanceTask,
    MaintenanceVisit,
    Material,
    MaterialRequirement,
    PersonnelStatus,
    User,
    Workshop,
)

bp = Blueprint("maintenance", __name__, url_prefix="/maintenance")


@bp.route("/")
@login_required
def index():
    status = request.args.get("status")
    query = MaintenanceVisit.query
    if status:
        query = query.filter_by(status=status)
    visits = query.order_by(MaintenanceVisit.start_date.desc()).all()
    aircrafts = Aircraft.query.order_by(Aircraft.tail_number).all()
    return render_template("maintenance/index.html", visits=visits, aircrafts=aircrafts)


@bp.route("/create", methods=["POST"])
@login_required
def create():
    aircraft_id = request.form.get("aircraft_id", type=int)
    vp_type = request.form.get("vp_type")
    name = request.form.get("name")
    start_date_str = request.form.get("start_date")
    if not all([aircraft_id, vp_type, name, start_date_str]):
        flash("Merci de fournir tous les champs requis", "danger")
        return redirect(url_for("maintenance.index"))

    start_date = date.fromisoformat(start_date_str)
    visit = MaintenanceVisit(
        name=name,
        aircraft_id=aircraft_id,
        vp_type=vp_type,
        status=request.form.get("status", "planned"),
        start_date=start_date,
        end_date=date.fromisoformat(request.form["end_date"]) if request.form.get("end_date") else None,
        description=request.form.get("description"),
    )
    db.session.add(visit)
    db.session.commit()
    flash("Visite programmée", "success")
    return redirect(url_for("maintenance.detail", visit_id=visit.id))


@bp.route("/<int:visit_id>")
@login_required
def detail(visit_id: int):
    visit = MaintenanceVisit.query.get_or_404(visit_id)
    workshops = Workshop.query.order_by(Workshop.name).all()
    personnel = User.query.order_by(User.rank.desc()).all()
    materials = Material.query.order_by(Material.designation).all()
    statuses = PersonnelStatus.query.filter_by(status="on-site").all()
    return render_template(
        "maintenance/detail.html",
        visit=visit,
        workshops=workshops,
        personnel=personnel,
        materials=materials,
        statuses=statuses,
    )


@bp.route("/<int:visit_id>/tasks", methods=["POST"])
@login_required
def add_task(visit_id: int):
    visit = MaintenanceVisit.query.get_or_404(visit_id)
    name = request.form.get("name")
    workshop_id = request.form.get("workshop_id", type=int)
    lead_id = request.form.get("lead_id", type=int)
    estimated_hours = request.form.get("estimated_hours", type=float, default=0.0)
    if not name:
        flash("Le nom de la tâche est obligatoire", "danger")
        return redirect(url_for("maintenance.detail", visit_id=visit.id))

    task = MaintenanceTask(
        visit=visit,
        name=name,
        workshop_id=workshop_id,
        lead_id=lead_id,
        estimated_hours=estimated_hours,
        status=request.form.get("status", "pending"),
    )
    db.session.add(task)
    db.session.commit()
    flash("Tâche ajoutée", "success")
    return redirect(url_for("maintenance.detail", visit_id=visit.id))


@bp.route("/tasks/<int:task_id>/status", methods=["POST"])
@login_required
def update_task_status(task_id: int):
    task = MaintenanceTask.query.get_or_404(task_id)
    status = request.form.get("status")
    if status:
        task.status = status
    started_at = request.form.get("started_at")
    completed_at = request.form.get("completed_at")
    if started_at:
        task.started_at = datetime.fromisoformat(started_at)
    if completed_at:
        task.completed_at = datetime.fromisoformat(completed_at)
    task.interruption_reason = request.form.get("interruption_reason")
    db.session.commit()
    flash("Tâche mise à jour", "success")
    return redirect(url_for("maintenance.detail", visit_id=task.visit_id))


@bp.route("/tasks/<int:task_id>/materials", methods=["POST"])
@login_required
def update_task_materials(task_id: int):
    task = MaintenanceTask.query.get_or_404(task_id)
    material_id = request.form.get("material_id", type=int)
    quantity = request.form.get("quantity", type=int, default=1)
    if not material_id:
        flash("Veuillez sélectionner un matériel", "danger")
        return redirect(url_for("maintenance.detail", visit_id=task.visit_id))

    requirement = MaterialRequirement.query.filter_by(task_id=task.id, material_id=material_id).first()
    if requirement:
        requirement.quantity = quantity
    else:
        requirement = MaterialRequirement(task=task, material_id=material_id, quantity=quantity)
        db.session.add(requirement)
    db.session.commit()
    flash("Besoin en matériel mis à jour", "success")
    return redirect(url_for("maintenance.detail", visit_id=task.visit_id))
