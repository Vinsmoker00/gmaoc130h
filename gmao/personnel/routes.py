from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models import PersonnelStatus, User, Workshop

bp = Blueprint("personnel", __name__, url_prefix="/personnel")


@bp.route("/")
@login_required
def index():
    status_filter = request.args.get("status")
    query = User.query
    if status_filter:
        query = query.join(PersonnelStatus).filter(PersonnelStatus.status == status_filter)
    users = query.order_by(User.rank.desc()).all()
    statuses = PersonnelStatus.query.order_by(PersonnelStatus.start_date.desc()).all()
    latest_status = {}
    for record in statuses:
        latest_status.setdefault(record.personnel_id, record)
    status_options = sorted({record.status for record in statuses})
    workshops = Workshop.query.order_by(Workshop.name).all()
    return render_template(
        "personnel/index.html",
        users=users,
        statuses=statuses,
        latest_status=latest_status,
        status_options=status_options,
        status_filter=status_filter,
        workshops=workshops,
        manage_mode=False,
    )


@bp.route("/<int:user_id>/status", methods=["POST"])
@login_required
def update_status(user_id: int):
    user = User.query.get_or_404(user_id)
    status = request.form.get("status")
    if not status:
        flash("Le statut est obligatoire", "danger")
        return redirect(url_for("personnel.index"))

    start_date_str = request.form.get("start_date")
    end_date_str = request.form.get("end_date")
    start_date = date.fromisoformat(start_date_str) if start_date_str else date.today()
    end_date = date.fromisoformat(end_date_str) if end_date_str else None

    record = PersonnelStatus(
        personnel=user,
        status=status,
        details=request.form.get("details"),
        start_date=start_date,
        end_date=end_date,
    )
    db.session.add(record)
    db.session.commit()
    flash("Statut mis à jour", "success")
    return redirect(url_for("personnel.index"))
