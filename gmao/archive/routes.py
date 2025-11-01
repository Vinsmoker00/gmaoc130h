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
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import (
    JobCard,
    JobCardAttachment,
    JobCardMaterial,
    JobCardParagraph,
    JobCardStep,
    JobCardSubstep,
    Material,
    Workshop,
)
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


@bp.route("/<int:card_id>")
@login_required
def card_detail(card_id: int):
    card = (
        JobCard.query.options(
            selectinload(JobCard.paragraphs)
            .selectinload(JobCardParagraph.steps)
            .selectinload(JobCardStep.substeps),
            selectinload(JobCard.steps).selectinload(JobCardStep.substeps),
            selectinload(JobCard.material_assignments).selectinload(JobCardMaterial.material),
        )
        .filter_by(id=card_id)
        .first_or_404()
    )
    workshops = Workshop.query.order_by(Workshop.name).all()
    materials = Material.query.order_by(Material.designation).all()
    return render_template(
        "archive/card_detail.html",
        card=card,
        workshops=workshops,
        materials=materials,
    )


@bp.route("/<int:card_id>/update", methods=["POST"])
@login_required
def update_card(card_id: int):
    card = JobCard.query.get_or_404(card_id)
    card.card_number = (request.form.get("card_number") or card.card_number).strip()
    card.title = (request.form.get("title") or card.title).strip()
    card.revision = (request.form.get("revision") or "").strip() or None
    card.summary = (request.form.get("summary") or "").strip() or None
    card.content = (request.form.get("content") or "").strip() or None
    db.session.commit()
    flash("Job card mise à jour", "success")
    return redirect(url_for("archive.card_detail", card_id=card.id))


@bp.route("/<int:card_id>/delete", methods=["POST"])
@login_required
def delete_card(card_id: int):
    card = JobCard.query.get_or_404(card_id)
    db.session.delete(card)
    db.session.commit()
    flash("Job card supprimée", "success")
    return redirect(url_for("archive.index"))


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


@bp.route("/attachments/<int:attachment_id>/delete", methods=["POST"])
@login_required
def delete_attachment(attachment_id: int):
    attachment = JobCardAttachment.query.get_or_404(attachment_id)
    card_id = attachment.job_card_id
    db.session.delete(attachment)
    db.session.commit()
    flash("Pièce jointe supprimée", "success")
    return redirect(url_for("archive.card_detail", card_id=card_id))


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


@bp.route("/<int:card_id>/paragraphs", methods=["POST"])
@login_required
def add_paragraph(card_id: int):
    card = JobCard.query.get_or_404(card_id)
    title = (request.form.get("title") or "").strip()
    if not title:
        flash("Merci d'indiquer un titre de paragraphe.", "danger")
        return redirect(url_for("archive.card_detail", card_id=card.id))
    paragraph = JobCardParagraph(
        job_card=card,
        title=title,
        description=(request.form.get("description") or "").strip() or None,
        order_index=request.form.get("order_index", type=int, default=card.paragraphs.__len__()),
        workshop_id=request.form.get("workshop_id", type=int),
        estimated_minutes=request.form.get("estimated_minutes", type=int, default=0),
    )
    db.session.add(paragraph)
    db.session.commit()
    flash("Paragraphe ajouté.", "success")
    return redirect(url_for("archive.card_detail", card_id=card.id))


@bp.route("/paragraphs/<int:paragraph_id>/update", methods=["POST"])
@login_required
def update_paragraph(paragraph_id: int):
    paragraph = JobCardParagraph.query.get_or_404(paragraph_id)
    paragraph.title = (request.form.get("title") or paragraph.title).strip()
    paragraph.description = (request.form.get("description") or "").strip() or None
    paragraph.order_index = request.form.get("order_index", type=int, default=paragraph.order_index)
    paragraph.workshop_id = request.form.get("workshop_id", type=int)
    paragraph.estimated_minutes = request.form.get(
        "estimated_minutes", type=int, default=paragraph.estimated_minutes
    )
    db.session.commit()
    flash("Paragraphe mis à jour.", "success")
    return redirect(url_for("archive.card_detail", card_id=paragraph.job_card_id))


@bp.route("/paragraphs/<int:paragraph_id>/delete", methods=["POST"])
@login_required
def delete_paragraph(paragraph_id: int):
    paragraph = JobCardParagraph.query.get_or_404(paragraph_id)
    card_id = paragraph.job_card_id
    db.session.delete(paragraph)
    db.session.commit()
    flash("Paragraphe supprimé.", "success")
    return redirect(url_for("archive.card_detail", card_id=card_id))


@bp.route("/<int:card_id>/steps", methods=["POST"])
@login_required
def add_step(card_id: int):
    card = JobCard.query.get_or_404(card_id)
    description = (request.form.get("description") or "").strip()
    if not description:
        flash("Décrivez l'étape avant de l'enregistrer.", "danger")
        return redirect(url_for("archive.card_detail", card_id=card.id))
    paragraph_id = request.form.get("paragraph_id", type=int)
    paragraph = None
    if paragraph_id:
        paragraph = JobCardParagraph.query.filter_by(id=paragraph_id, job_card_id=card.id).first()
        if paragraph is None:
            flash("Paragraphe introuvable pour cette job card.", "danger")
            return redirect(url_for("archive.card_detail", card_id=card.id))
    step = JobCardStep(
        job_card=card,
        paragraph=paragraph,
        title=(request.form.get("title") or "").strip() or None,
        description=description,
        order_index=request.form.get("order_index", type=int, default=0),
        workshop_id=request.form.get("workshop_id", type=int),
        estimated_minutes=request.form.get("estimated_minutes", type=int, default=0),
    )
    db.session.add(step)
    db.session.commit()
    flash("Étape ajoutée.", "success")
    return redirect(url_for("archive.card_detail", card_id=card.id))


@bp.route("/steps/<int:step_id>/update", methods=["POST"])
@login_required
def update_step(step_id: int):
    step = JobCardStep.query.get_or_404(step_id)
    step.title = (request.form.get("title") or "").strip() or None
    step.description = (request.form.get("description") or step.description).strip()
    step.order_index = request.form.get("order_index", type=int, default=step.order_index)
    step.workshop_id = request.form.get("workshop_id", type=int)
    step.estimated_minutes = request.form.get("estimated_minutes", type=int, default=step.estimated_minutes)
    step.paragraph_id = request.form.get("paragraph_id", type=int)
    db.session.commit()
    flash("Étape mise à jour.", "success")
    return redirect(url_for("archive.card_detail", card_id=step.job_card_id))


@bp.route("/steps/<int:step_id>/delete", methods=["POST"])
@login_required
def delete_step(step_id: int):
    step = JobCardStep.query.get_or_404(step_id)
    card_id = step.job_card_id
    db.session.delete(step)
    db.session.commit()
    flash("Étape supprimée.", "success")
    return redirect(url_for("archive.card_detail", card_id=card_id))


@bp.route("/<int:card_id>/substeps", methods=["POST"])
@login_required
def add_substep(card_id: int):
    card = JobCard.query.get_or_404(card_id)
    step_id = request.form.get("step_id", type=int)
    step = JobCardStep.query.filter_by(id=step_id, job_card_id=card.id).first()
    if step is None:
        flash("Étape introuvable pour cette job card.", "danger")
        return redirect(url_for("archive.card_detail", card_id=card.id))
    description = (request.form.get("description") or "").strip()
    if not description:
        flash("Merci de décrire la sous-étape.", "danger")
        return redirect(url_for("archive.card_detail", card_id=card.id))
    substep = JobCardSubstep(
        job_card=card,
        step=step,
        description=description,
        order_index=request.form.get("order_index", type=int, default=0),
        workshop_id=request.form.get("workshop_id", type=int),
        estimated_minutes=request.form.get("estimated_minutes", type=int, default=0),
    )
    db.session.add(substep)
    db.session.commit()
    flash("Sous-étape ajoutée.", "success")
    return redirect(url_for("archive.card_detail", card_id=card.id))


@bp.route("/substeps/<int:substep_id>/update", methods=["POST"])
@login_required
def update_substep(substep_id: int):
    substep = JobCardSubstep.query.get_or_404(substep_id)
    substep.description = (request.form.get("description") or substep.description).strip()
    substep.order_index = request.form.get("order_index", type=int, default=substep.order_index)
    substep.workshop_id = request.form.get("workshop_id", type=int)
    substep.estimated_minutes = request.form.get(
        "estimated_minutes", type=int, default=substep.estimated_minutes
    )
    db.session.commit()
    flash("Sous-étape mise à jour.", "success")
    return redirect(url_for("archive.card_detail", card_id=substep.job_card_id))


@bp.route("/substeps/<int:substep_id>/delete", methods=["POST"])
@login_required
def delete_substep(substep_id: int):
    substep = JobCardSubstep.query.get_or_404(substep_id)
    card_id = substep.job_card_id
    db.session.delete(substep)
    db.session.commit()
    flash("Sous-étape supprimée.", "success")
    return redirect(url_for("archive.card_detail", card_id=card_id))


@bp.route("/<int:card_id>/materials", methods=["POST"])
@login_required
def add_job_card_material(card_id: int):
    card = JobCard.query.get_or_404(card_id)
    material_id = request.form.get("material_id", type=int)
    if not material_id:
        flash("Sélectionnez un matériel.", "danger")
        return redirect(url_for("archive.card_detail", card_id=card.id))
    paragraph_id = request.form.get("paragraph_id", type=int)
    step_id = request.form.get("step_id", type=int)
    substep_id = request.form.get("substep_id", type=int)
    target_count = sum(1 for value in [paragraph_id, step_id, substep_id] if value)
    if target_count > 1:
        flash("Choisissez un seul niveau (paragraphe, étape ou sous-étape).", "danger")
        return redirect(url_for("archive.card_detail", card_id=card.id))
    if paragraph_id:
        paragraph = JobCardParagraph.query.filter_by(id=paragraph_id, job_card_id=card.id).first()
        if paragraph is None:
            flash("Paragraphe inconnu.", "danger")
            return redirect(url_for("archive.card_detail", card_id=card.id))
    if step_id:
        step = JobCardStep.query.filter_by(id=step_id, job_card_id=card.id).first()
        if step is None:
            flash("Étape inconnue.", "danger")
            return redirect(url_for("archive.card_detail", card_id=card.id))
    if substep_id:
        substep = JobCardSubstep.query.filter_by(id=substep_id, job_card_id=card.id).first()
        if substep is None:
            flash("Sous-étape inconnue.", "danger")
            return redirect(url_for("archive.card_detail", card_id=card.id))
    assignment = JobCardMaterial(
        job_card=card,
        material_id=material_id,
        paragraph_id=paragraph_id,
        step_id=step_id,
        substep_id=substep_id,
        quantity=request.form.get("quantity", type=float, default=1.0),
        notes=(request.form.get("notes") or "").strip() or None,
    )
    db.session.add(assignment)
    db.session.commit()
    flash("Matériel associé.", "success")
    return redirect(url_for("archive.card_detail", card_id=card.id))


@bp.route("/materials/<int:assignment_id>/delete", methods=["POST"])
@login_required
def delete_job_card_material(assignment_id: int):
    assignment = JobCardMaterial.query.get_or_404(assignment_id)
    card_id = assignment.job_card_id
    db.session.delete(assignment)
    db.session.commit()
    flash("Association matériel supprimée.", "success")
    return redirect(url_for("archive.card_detail", card_id=card_id))
