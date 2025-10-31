from datetime import date, datetime

from typing import Dict, Iterable, List

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models import (
    Aircraft,
    JobCard,
    MaintenanceTask,
    MaintenanceVisit,
    Material,
    MaterialRequirement,
    PersonnelStatus,
    User,
    Workshop,
)
from .packages import normalize_visit_type, package_for_visit

PACKAGE_PERIODICITY_MONTHS = {
    "A": 9,
    "B": 18,
    "C": 36,
    "D1": 72,
    "D2": 144,
}

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

    created_tasks, missing_cards = _populate_visit_from_package(visit)
    if created_tasks:
        db.session.commit()
        flash(
            f"{len(created_tasks)} tâches package ajoutées automatiquement.",
            "success",
        )
    else:
        flash("Visite programmée", "success")
    if missing_cards:
        flash(
            "Job cards manquantes dans l'archive : " + ", ".join(sorted(missing_cards)),
            "warning",
        )
    return redirect(url_for("maintenance.detail", visit_id=visit.id))


@bp.route("/<int:visit_id>")
@login_required
def detail(visit_id: int):
    visit = MaintenanceVisit.query.get_or_404(visit_id)
    workshops = Workshop.query.order_by(Workshop.name).all()
    personnel = User.query.order_by(User.rank.desc()).all()
    materials = Material.query.order_by(Material.designation).all()
    statuses = PersonnelStatus.query.filter_by(status="on-site").all()
    job_cards = JobCard.query.order_by(JobCard.card_number).all()
    tasks = visit.tasks.order_by(MaintenanceTask.name).all()
    package_codes = package_for_visit(visit.vp_type)
    package_status = _package_status(visit, tasks, package_codes)
    material_totals = _aggregate_visit_materials(tasks)
    periodicity = PACKAGE_PERIODICITY_MONTHS.get(package_status["vp_key"], None)
    return render_template(
        "maintenance/detail.html",
        visit=visit,
        workshops=workshops,
        personnel=personnel,
        materials=materials,
        statuses=statuses,
        job_cards=job_cards,
        tasks=tasks,
        package_status=package_status,
        package_codes=package_codes,
        material_totals=material_totals,
        periodicity_months=periodicity,
    )


@bp.route("/<int:visit_id>/package/sync", methods=["POST"])
@login_required
def sync_package(visit_id: int):
    visit = MaintenanceVisit.query.get_or_404(visit_id)
    created_tasks, missing_cards = _populate_visit_from_package(visit)
    relinked = _attach_available_job_cards(visit)
    if created_tasks or relinked:
        db.session.commit()
        flash("Package synchronisé avec l'archive.", "success")
    if missing_cards:
        flash(
            "Job cards manquantes dans l'archive : " + ", ".join(sorted(missing_cards)),
            "warning",
        )
    return redirect(url_for("maintenance.detail", visit_id=visit.id))


@bp.route("/<int:visit_id>/tasks", methods=["POST"])
@login_required
def add_task(visit_id: int):
    visit = MaintenanceVisit.query.get_or_404(visit_id)
    description = (request.form.get("description") or "").strip()
    workshop_id = request.form.get("workshop_id", type=int)
    lead_id = request.form.get("lead_id", type=int)
    estimated_hours = request.form.get("estimated_hours", type=float, default=0.0)
    job_card_id = request.form.get("job_card_id", type=int)
    job_card = None
    if job_card_id:
        job_card = JobCard.query.get(job_card_id)
        if job_card is None:
            flash("Job card sélectionnée invalide", "danger")
            return redirect(url_for("maintenance.detail", visit_id=visit.id))

    task_name = description or (job_card.title if job_card else "")
    if not task_name:
        flash("Renseignez une description ou sélectionnez une job card.", "danger")
        return redirect(url_for("maintenance.detail", visit_id=visit.id))

    task = MaintenanceTask(
        visit=visit,
        name=task_name,
        workshop_id=workshop_id,
        lead_id=lead_id,
        job_card_id=job_card.id if job_card else None,
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


def _populate_visit_from_package(visit: MaintenanceVisit):
    package_codes = package_for_visit(visit.vp_type)
    created_tasks: List[MaintenanceTask] = []
    missing_cards: List[str] = []
    existing_codes = {
        task.package_code
        for task in MaintenanceTask.query.filter_by(visit_id=visit.id, is_package_item=True)
        if task.package_code
    }
    for code in package_codes:
        if code in existing_codes:
            continue
        job_card = JobCard.query.filter_by(card_number=code).first()
        if job_card:
            name = f"{code} · {job_card.title}"
            estimated_hours = job_card.estimated_hours
        else:
            missing_cards.append(code)
            name = f"{code} (à compléter)"
            estimated_hours = 0.0
        task = MaintenanceTask(
            visit=visit,
            name=name,
            job_card=job_card,
            status="pending",
            estimated_hours=estimated_hours,
            is_package_item=True,
            package_code=code,
        )
        db.session.add(task)
        created_tasks.append(task)
    return created_tasks, missing_cards


def _attach_available_job_cards(visit: MaintenanceVisit):
    relinked: List[MaintenanceTask] = []
    package_tasks = MaintenanceTask.query.filter_by(visit_id=visit.id, is_package_item=True).all()
    for task in package_tasks:
        if not task.is_package_item or task.job_card_id:
            continue
        if not task.package_code:
            continue
        job_card = JobCard.query.filter_by(card_number=task.package_code).first()
        if job_card is None:
            continue
        task.job_card = job_card
        task.name = f"{task.package_code} · {job_card.title}"
        task.estimated_hours = job_card.estimated_hours
        relinked.append(task)
    return relinked


def _package_status(
    visit: MaintenanceVisit,
    tasks: Iterable[MaintenanceTask],
    package_codes: Iterable[str],
) -> Dict[str, object]:
    task_by_code: Dict[str, MaintenanceTask] = {}
    completed = 0
    for task in tasks:
        if task.is_package_item and task.package_code:
            task_by_code[task.package_code] = task
            if task.status == "completed":
                completed += 1
    overview = []
    for code in package_codes:
        task = task_by_code.get(code)
        overview.append(
            {
                "code": code,
                "task": task,
                "job_card": task.job_card if task else JobCard.query.filter_by(card_number=code).first(),
                "status": task.status if task else "missing",
            }
        )
    total = len(package_codes)
    return {
        "vp_key": normalize_visit_type(visit.vp_type),
        "overview": overview,
        "total": total,
        "completed": completed,
        "available": len(task_by_code),
        "missing": [code for code in package_codes if code not in task_by_code],
    }


def _aggregate_visit_materials(tasks: Iterable[MaintenanceTask]):
    aggregated: Dict[int, Dict[str, object]] = {}
    for task in tasks:
        for requirement in task.materials:
            entry = aggregated.setdefault(
                requirement.material_id,
                {
                    "material": requirement.material,
                    "job_card_quantity": 0.0,
                    "additional_quantity": 0.0,
                },
            )
            entry["additional_quantity"] += requirement.quantity or 0
        if task.job_card is None:
            continue
        for assignment in task.job_card.material_assignments:
            entry = aggregated.setdefault(
                assignment.material_id,
                {
                    "material": assignment.material,
                    "job_card_quantity": 0.0,
                    "additional_quantity": 0.0,
                },
            )
            entry["job_card_quantity"] += assignment.quantity or 0
    return sorted(
        aggregated.values(),
        key=lambda item: item["material"].designation if item["material"] else "",
    )
