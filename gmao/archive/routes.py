from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models import JobCard, JobCardAttachment

bp = Blueprint("archive", __name__, url_prefix="/archive")


@bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    query = JobCard.query
    if search:
        query = query.filter(JobCard.title.contains(search) | JobCard.card_number.contains(search))
    cards = query.order_by(JobCard.card_number).all()
    return render_template("archive/index.html", cards=cards, search=search)


@bp.route("/create", methods=["POST"])
@login_required
def create():
    card_number = request.form.get("card_number")
    title = request.form.get("title")
    if not card_number or not title:
        flash("Le numéro et le titre sont obligatoires", "danger")
        return redirect(url_for("archive.index"))

    card = JobCard(
        card_number=card_number,
        title=title,
        revision=request.form.get("revision"),
        summary=request.form.get("summary"),
        content=request.form.get("content"),
    )
    db.session.add(card)
    db.session.commit()
    flash("Job card ajoutée", "success")
    return redirect(url_for("archive.index"))


@bp.route("/<int:card_id>/attachments", methods=["POST"])
@login_required
def add_attachment(card_id: int):
    card = JobCard.query.get_or_404(card_id)
    filename = request.form.get("filename")
    if not filename:
        flash("Nom du fichier requis", "danger")
        return redirect(url_for("archive.index"))

    attachment = JobCardAttachment(job_card=card, filename=filename, original_name=request.form.get("original_name"))
    db.session.add(attachment)
    db.session.commit()
    flash("Pièce jointe ajoutée", "success")
    return redirect(url_for("archive.index"))
