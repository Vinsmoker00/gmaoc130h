from typing import Optional

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..extensions import db
from ..models import Material, MaterialRequirement

bp = Blueprint("materials", __name__, url_prefix="/materials")


@bp.route("/")
@login_required
def index():
    category = request.args.get("category")
    query = Material.query
    if category:
        query = query.filter_by(category=category)
    materials = query.order_by(Material.designation).all()
    categories = sorted({material.category for material in Material.query.all()})
    return render_template("materials/index.html", materials=materials, categories=categories)


@bp.route("/create", methods=["POST"])
@login_required
def create():
    designation = (request.form.get("designation") or "").strip()
    category = (request.form.get("category") or "").strip()
    if not designation or not category:
        flash("Les champs désignation et catégorie sont obligatoires", "danger")
        return redirect(url_for("materials.index"))

    def parse_int_field(name: str, default: int = 0) -> int:
        value = request.form.get(name)
        if value is None:
            return default
        value = value.strip()
        if value == "":
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def parse_string_field(name: str) -> Optional[str]:
        value = request.form.get(name)
        if value is None:
            return None
        value = value.strip()
        return value or None

    material = Material(
        designation=designation,
        category=category,
        part_number=parse_string_field("part_number"),
        serial_number=parse_string_field("serial_number"),
        nsn=parse_string_field("nsn"),
        niin=parse_string_field("niin"),
        fsc=parse_string_field("fsc"),
        cage_code=parse_string_field("cage_code"),
        dotation=parse_int_field("dotation"),
        avionnee=parse_int_field("avionnee"),
        stock=parse_int_field("stock"),
        unavailable_for_repair=parse_int_field("unavailable_for_repair"),
        in_repair=parse_int_field("in_repair"),
        annual_consumption=parse_int_field("annual_consumption"),
        consumable_stock=parse_int_field("consumable_stock"),
        consumable_dotation=parse_int_field("consumable_dotation"),
        consumable_type=parse_string_field("consumable_type"),
        contract_type=parse_string_field("contract_type"),
        da_reference=parse_string_field("da_reference"),
        da_status=parse_string_field("da_status"),
        per_aircraft=parse_int_field("per_aircraft", default=1),
        warranty=request.form.get("warranty") == "on",
    )
    db.session.add(material)
    db.session.commit()
    flash("Matériel ajouté", "success")
    return redirect(url_for("materials.index"))


@bp.route("/<int:material_id>")
@login_required
def detail(material_id: int):
    material = Material.query.get_or_404(material_id)
    requirements = MaterialRequirement.query.filter_by(material_id=material.id).all()
    return render_template("materials/detail.html", material=material, requirements=requirements)


@bp.route("/<int:material_id>/update", methods=["POST"])
@login_required
def update(material_id: int):
    material = Material.query.get_or_404(material_id)

    int_fields = [
        "dotation",
        "avionnee",
        "stock",
        "unavailable_for_repair",
        "in_repair",
        "litigation",
        "scrapped",
        "per_aircraft",
        "annual_consumption",
        "consumable_stock",
        "consumable_dotation",
    ]
    for field in int_fields:
        if field in request.form and request.form[field] != "":
            setattr(material, field, request.form.get(field, type=int))

    def cleaned_value(field_name: str) -> Optional[str]:
        if field_name not in request.form:
            return getattr(material, field_name)
        value = (request.form.get(field_name) or "").strip()
        return value or None

    string_fields = [
        "designation",
        "part_number",
        "serial_number",
        "nsn",
        "niin",
        "fsc",
        "cage_code",
        "da_status",
        "da_reference",
        "contract_type",
        "consumable_type",
    ]
    for field in string_fields:
        setattr(material, field, cleaned_value(field))

    if "category" in request.form and request.form["category"]:
        material.category = request.form["category"]

    material.warranty = request.form.get("warranty") == "on"

    db.session.commit()
    flash("Fiche matériel mise à jour", "success")
    return redirect(url_for("materials.detail", material_id=material_id))


@bp.route("/<int:material_id>/delete", methods=["POST"])
@login_required
def delete(material_id: int):
    material = Material.query.get_or_404(material_id)
    db.session.delete(material)
    db.session.commit()
    flash("Matériel supprimé", "success")
    return redirect(url_for("materials.index"))
