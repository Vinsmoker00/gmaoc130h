from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import login_required
from ..extensions import db
from ..models import JobCard, JobCardAttachment
from ..utils import UploadError, save_job_card_file

bp = Blueprint("archive", __name__, url_prefix="/archive")


@bp.route("/")
@login_required
def index():
    search = request.args.get("search", "").strip()
    query = JobCard.query
    if search:
        query = query.filter(JobCard.title.contains(search) | JobCard.card_number.contains(search))
    cards = query.order_by(JobCard.card_number).all()
    attachments_by_card = {
        card.id: card.attachments.order_by(JobCardAttachment.uploaded_at.desc()).all()
        for card in cards
    }
    return render_template(
        "archive/index.html", cards=cards, search=search, attachments_by_card=attachments_by_card
    )


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
    file = request.files.get("attachment")
    if file is None:
        flash("Merci de sélectionner un fichier PDF.", "danger")
        return redirect(url_for("archive.index"))

    try:
        stored_name, relative_path, mimetype, original_name = save_job_card_file(
            file, card.id, current_app.config
        )
    except UploadError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("archive.index"))
    except OSError:
        current_app.logger.exception("Erreur lors de l'enregistrement de la pièce jointe")
        flash("Impossible d'enregistrer le fichier pour le moment.", "danger")
        return redirect(url_for("archive.index"))

    attachment = JobCardAttachment(
        job_card=card,
        filename=stored_name,
        original_name=original_name,
        file_path=relative_path,
        mime_type=mimetype,
    )
    db.session.add(attachment)
    db.session.commit()
    flash("Pièce jointe ajoutée", "success")
    return redirect(url_for("archive.index"))


@bp.route("/attachments/<int:attachment_id>")
@login_required
def download_attachment(attachment_id: int):
    attachment = JobCardAttachment.query.get_or_404(attachment_id)
    upload_root = Path(current_app.config["UPLOAD_ROOT"]).expanduser()
    file_path = upload_root / attachment.file_path
    if not file_path.exists():
        flash("Fichier introuvable sur le serveur.", "danger")
        return redirect(url_for("archive.index"))

    return send_from_directory(
        str(upload_root),
        attachment.file_path,
        as_attachment=True,
        download_name=attachment.original_name or attachment.filename,
        mimetype=attachment.mime_type or "application/pdf",
    )
