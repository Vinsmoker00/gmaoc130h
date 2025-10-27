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
