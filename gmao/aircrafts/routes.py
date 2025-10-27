from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models import Aircraft, MaintenanceVisit

bp = Blueprint("aircrafts", __name__, url_prefix="/aircrafts")


@bp.route("/")
@login_required
def index():
    aircrafts = Aircraft.query.order_by(Aircraft.tail_number).all()
    return render_template("aircrafts/index.html", aircrafts=aircrafts)


@bp.route("/create", methods=["POST"])
@login_required
def create():
    tail_number = request.form.get("tail_number")
    if not tail_number:
        flash("Le matricule est obligatoire", "danger")
        return redirect(url_for("aircrafts.index"))

    aircraft = Aircraft(
        tail_number=tail_number,
        aircraft_type=request.form.get("aircraft_type", "C-130H"),
        location=request.form.get("location"),
        status=request.form.get("status", "available"),
        notes=request.form.get("notes"),
    )
    db.session.add(aircraft)
    db.session.commit()
    flash("Nouvel aéronef ajouté", "success")
    return redirect(url_for("aircrafts.index"))


@bp.route("/<int:aircraft_id>")
@login_required
def detail(aircraft_id: int):
    aircraft = Aircraft.query.get_or_404(aircraft_id)
    visits = MaintenanceVisit.query.filter_by(aircraft_id=aircraft.id).order_by(MaintenanceVisit.start_date.desc()).all()
    return render_template("aircrafts/detail.html", aircraft=aircraft, visits=visits)


@bp.route("/<int:aircraft_id>/update", methods=["POST"])
@login_required
def update(aircraft_id: int):
    aircraft = Aircraft.query.get_or_404(aircraft_id)
    aircraft.location = request.form.get("location", aircraft.location)
    aircraft.status = request.form.get("status", aircraft.status)
    aircraft.notes = request.form.get("notes", aircraft.notes)
    db.session.commit()
    flash("Informations mises à jour", "success")
    return redirect(url_for("aircrafts.detail", aircraft_id=aircraft_id))
