from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import List

from flask import Blueprint, jsonify, render_template, url_for
from flask_login import login_required

from ..models import MaintenanceTask, MaintenanceVisit
from ..utils.scheduling import compute_critical_path

bp = Blueprint("gantt", __name__, url_prefix="/gantt")


@bp.route("/")
@login_required
def index():
    visits = (
        MaintenanceVisit.query.order_by(MaintenanceVisit.start_date.desc(), MaintenanceVisit.id.desc()).all()
    )
    return render_template("gantt/index.html", visits=visits)


@bp.route("/<int:visit_id>")
@login_required
def detail(visit_id: int):
    visit = MaintenanceVisit.query.get_or_404(visit_id)
    return render_template("gantt/detail.html", visit=visit)


@bp.route("/<int:visit_id>/data")
@login_required
def visit_data(visit_id: int):
    visit = MaintenanceVisit.query.get_or_404(visit_id)
    tasks: List[MaintenanceTask] = (
        visit.tasks.order_by(MaintenanceTask.started_at.asc(), MaintenanceTask.id.asc()).all()
    )

    tasks = sorted(
        tasks,
        key=lambda task: (
            task.started_at or datetime.combine(visit.start_date, time.min),
            task.id,
        ),
    )

    task_payload = []
    base_start = datetime.combine(visit.start_date, time.min)
    for index, task in enumerate(tasks):
        if task.started_at and task.completed_at:
            duration_hours = max((task.completed_at - task.started_at).total_seconds() / 3600.0, 0.0)
        else:
            duration_hours = float(task.estimated_hours or 0.0)
        if duration_hours <= 0:
            duration_hours = 1.0
        task_payload.append(
            {
                "id": task.id,
                "duration": duration_hours,
                "dependencies": [],
                "order": index,
                "_model": task,
            }
        )

    schedule = compute_critical_path(task_payload)
    schedule_map = {item.id: item for item in schedule["tasks"]}
    critical_ids = set(schedule["critical_path"])

    tasks_json = []
    for entry in task_payload:
        model = entry["_model"]
        schedule_entry = schedule_map.get(model.id)
        if schedule_entry is None:
            continue
        computed_start = base_start + timedelta(hours=schedule_entry.start)
        computed_end = base_start + timedelta(hours=schedule_entry.finish)

        if model.started_at:
            start_at = model.started_at
        else:
            start_at = computed_start

        if model.completed_at:
            end_at = model.completed_at
        else:
            end_at = computed_end

        tasks_json.append(
            {
                "id": model.id,
                "name": model.name,
                "status": model.status,
                "lead": model.lead.full_name if model.lead else None,
                "workshop": model.workshop.name if model.workshop else None,
                "duration_hours": schedule_entry.duration,
                "start": start_at.isoformat(),
                "end": end_at.isoformat(),
                "earliest_start_hours": schedule_entry.start,
                "earliest_finish_hours": schedule_entry.finish,
                "is_critical": model.id in critical_ids,
            }
        )

    response = {
        "visit": {
            "id": visit.id,
            "name": visit.name,
            "start_date": visit.start_date.isoformat(),
            "end_date": visit.end_date.isoformat() if visit.end_date else None,
        },
        "project_duration_hours": schedule["project_duration"],
        "critical_path": schedule["critical_path"],
        "tasks": tasks_json,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    return jsonify(response)


@bp.app_context_processor
def inject_gantt_links():
    return {
        "gantt_visit_selector": [
            (visit.name, url_for("gantt.detail", visit_id=visit.id))
            for visit in MaintenanceVisit.query.order_by(MaintenanceVisit.start_date.desc()).all()
        ]
    }
