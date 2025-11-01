from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models import Material, Workshop, WorkshopMaterial

bp = Blueprint("workshops", __name__, url_prefix="/workshops")


@bp.route("/")
@login_required
def index():
    workshops = Workshop.query.order_by(Workshop.name).all()
    return render_template("workshops/index.html", workshops=workshops)


@bp.route("/create", methods=["POST"])
@login_required
def create():
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Le nom de l'atelier est obligatoire", "danger")
        return redirect(url_for("workshops.index"))
    description = (request.form.get("description") or "").strip() or None
    if Workshop.query.filter_by(name=name).first():
        flash("Un atelier avec ce nom existe déjà", "warning")
        return redirect(url_for("workshops.index"))
    workshop = Workshop(name=name, description=description)
    db.session.add(workshop)
    db.session.commit()
    flash("Atelier créé", "success")
    return redirect(url_for("workshops.detail", workshop_id=workshop.id))


@bp.route("/<int:workshop_id>")
@login_required
def detail(workshop_id: int):
    workshop = Workshop.query.get_or_404(workshop_id)
    materials = WorkshopMaterial.query.filter_by(workshop_id=workshop.id).all()
    all_materials = Material.query.order_by(Material.designation).all()
    return render_template(
        "workshops/detail.html",
        workshop=workshop,
        materials=materials,
        all_materials=all_materials,
    )


@bp.route("/<int:workshop_id>/update", methods=["POST"])
@login_required
def update(workshop_id: int):
    workshop = Workshop.query.get_or_404(workshop_id)
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Le nom est obligatoire", "danger")
        return redirect(url_for("workshops.detail", workshop_id=workshop.id))
    if Workshop.query.filter(Workshop.id != workshop.id, Workshop.name == name).first():
        flash("Ce nom est déjà utilisé", "warning")
        return redirect(url_for("workshops.detail", workshop_id=workshop.id))
    workshop.name = name
    workshop.description = (request.form.get("description") or "").strip() or None
    db.session.commit()
    flash("Atelier mis à jour", "success")
    return redirect(url_for("workshops.detail", workshop_id=workshop.id))


@bp.route("/<int:workshop_id>/delete", methods=["POST"])
@login_required
def delete(workshop_id: int):
    workshop = Workshop.query.get_or_404(workshop_id)
    db.session.delete(workshop)
    db.session.commit()
    flash("Atelier supprimé", "success")
    return redirect(url_for("workshops.index"))


@bp.route("/<int:workshop_id>/materials", methods=["POST"])
@login_required
def attach_material(workshop_id: int):
    workshop = Workshop.query.get_or_404(workshop_id)
    material_id = request.form.get("material_id")
    quantity = request.form.get("quantity", type=int, default=0)
    material = Material.query.get(material_id)
    if not material:
        flash("Matériel introuvable", "danger")
        return redirect(url_for("workshops.detail", workshop_id=workshop_id))

    record = WorkshopMaterial.query.filter_by(workshop_id=workshop.id, material_id=material.id).first()
    if record:
        record.quantity = quantity
    else:
        record = WorkshopMaterial(workshop=workshop, material=material, quantity=quantity)
        db.session.add(record)
    db.session.commit()
    flash("Matériel associé", "success")
    return redirect(url_for("workshops.detail", workshop_id=workshop_id))


@bp.route("/materials/<int:record_id>/delete", methods=["POST"])
@login_required
def detach_material(record_id: int):
    record = WorkshopMaterial.query.get_or_404(record_id)
    workshop_id = record.workshop_id
    db.session.delete(record)
    db.session.commit()
    flash("Matériel retiré", "success")
    return redirect(url_for("workshops.detail", workshop_id=workshop_id))
