from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Tuple

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import or_

from ..extensions import db
from ..models import (
    Aircraft,
    Material,
    MaterialRequirement,
    MaterialSerial,
    Workshop,
)

bp = Blueprint("materials", __name__, url_prefix="/materials")

DEFAULT_CATEGORY = "reparable"
CATEGORY_ORDER = ["reparable", "consommable", "outillage", "banc d'essai"]
SERIAL_STATUS_CHOICES: List[Tuple[str, str]] = [
    ("avionnee", "Avionnée"),
    ("att_rpn", "ATT RPN"),
    ("rpn", "RPN"),
    ("litige", "Litige"),
    ("nivellement", "Nivellement"),
    ("stock", "Stock"),
    ("sous_garantie", "Sous garantie"),
]


def _normalize_category(raw: Optional[str]) -> str:
    if not raw:
        return DEFAULT_CATEGORY
    raw = raw.strip().lower()
    return raw if raw in CATEGORY_ORDER else DEFAULT_CATEGORY


def _parse_int(field_name: str, default: int = 0) -> int:
    value = request.form.get(field_name)
    if value is None:
        return default
    value = value.strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_optional_int(field_name: str) -> Optional[int]:
    value = request.form.get(field_name)
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_optional_string(field_name: str) -> Optional[str]:
    value = request.form.get(field_name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _parse_optional_date(field_name: str) -> Optional[date]:
    value = request.form.get(field_name)
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@bp.route("/")
@login_required
def index():
    active_category = _normalize_category(request.args.get("category"))
    search_term = (request.args.get("search") or "").strip()

    query = Material.query.filter_by(category=active_category)
    if search_term:
        pattern = f"%{search_term}%"
        query = query.filter(
            or_(
                Material.designation.ilike(pattern),
                Material.part_number.ilike(pattern),
                Material.niin.ilike(pattern),
            )
        )

    materials = (
        query.order_by(Material.designation)
        .limit(50)
        .all()
    )

    counts: Dict[str, int] = {
        category: Material.query.filter_by(category=category).count()
        for category in CATEGORY_ORDER
    }

    critical_materials: List[Tuple[Material, List[str]]] = []
    for material in Material.query.order_by(Material.designation).all():
        issues = material.serial_data_issues()
        if issues:
            critical_materials.append((material, issues))
        if len(critical_materials) >= 12:
            break

    return render_template(
        "materials/index.html",
        active_category=active_category,
        materials=materials,
        categories=CATEGORY_ORDER,
        category_counts=counts,
        search_term=search_term,
        critical_materials=critical_materials,
        serial_status_choices=SERIAL_STATUS_CHOICES,
    )


@bp.route("/new")
@login_required
def new():
    workshops = Workshop.query.order_by(Workshop.name).all()
    aircraft = Aircraft.query.order_by(Aircraft.tail_number).all()
    return render_template(
        "materials/create.html",
        categories=CATEGORY_ORDER,
        workshops=workshops,
        aircraft=aircraft,
        serial_status_choices=SERIAL_STATUS_CHOICES,
    )


@bp.route("/create", methods=["POST"])
@login_required
def create():
    designation = (request.form.get("designation") or "").strip()
    category = _normalize_category(request.form.get("category"))

    if not designation:
        flash("La désignation est obligatoire.", "danger")
        return redirect(url_for("materials.new"))

    workshop_id = _parse_optional_int("workshop_id")

    material = Material(
        designation=designation,
        category=category,
        part_number=_parse_optional_string("part_number"),
        serial_number=_parse_optional_string("serial_number"),
        nsn=_parse_optional_string("nsn"),
        niin=_parse_optional_string("niin"),
        fsc=_parse_optional_string("fsc"),
        cage_code=_parse_optional_string("cage_code"),
        workshop_id=workshop_id,
    )

    if category == "reparable":
        dotation = max(_parse_int("dotation"), 0)
        material.per_aircraft = _parse_int("per_aircraft", default=0)
        material.annual_consumption = _parse_int("annual_consumption", default=0)

        db.session.add(material)
        db.session.flush()

        serials: List[MaterialSerial] = []
        for index in range(dotation):
            prefix = f"serials-{index}-"
            status = (_parse_optional_string(prefix + "status") or "stock").lower()
            if status not in {choice for choice, _ in SERIAL_STATUS_CHOICES}:
                status = "stock"
            under_warranty = request.form.get(prefix + "under_warranty") == "on"
            if status == "sous_garantie":
                under_warranty = True
            serial = MaterialSerial(
                material_id=material.id,
                serial_number=_parse_optional_string(prefix + "serial_number"),
                status=status,
                aircraft_id=_parse_optional_int(prefix + "aircraft_id"),
                da_reference=_parse_optional_string(prefix + "da_reference"),
                da_status=_parse_optional_string(prefix + "da_status"),
                notes=_parse_optional_string(prefix + "notes"),
                under_warranty=under_warranty,
            )
            serials.append(serial)
        if dotation and len(serials) != dotation:
            flash("La dotation doit correspondre au nombre de numéros de série saisis.", "danger")
            db.session.rollback()
            return redirect(url_for("materials.new"))
        for serial in serials:
            db.session.add(serial)
        material.recompute_status_counters()

    elif category == "consommable":
        stock_value = _parse_int("stock")
        material.stock = stock_value
        material.consumable_stock = stock_value
        material.rca_rcb_reference = _parse_optional_string("rca_rcb_reference")
        if stock_value == 0 and not material.rca_rcb_reference:
            flash(
                "Merci d'indiquer une référence RCA/RCB lorsque le stock est nul.",
                "danger",
            )
            return redirect(url_for("materials.new"))

    elif category in {"outillage", "banc d'essai"}:
        material.last_calibration_date = _parse_optional_date("last_calibration_date")
        material.calibration_expiration_date = _parse_optional_date(
            "calibration_expiration_date"
        )

    db.session.add(material)
    db.session.commit()

    flash("Matériel enregistré", "success")
    return redirect(url_for("materials.index", category=category))


@bp.route("/<int:material_id>")
@login_required
def detail(material_id: int):
    material = Material.query.get_or_404(material_id)
    requirements = MaterialRequirement.query.filter_by(material_id=material.id).all()
    serials = material.serials.order_by(MaterialSerial.serial_number).all()
    workshops = Workshop.query.order_by(Workshop.name).all()
    aircraft = Aircraft.query.order_by(Aircraft.tail_number).all()
    status_counts = material.serial_status_counts() if material.category == "reparable" else {}
    issues = material.serial_data_issues()

    return render_template(
        "materials/detail.html",
        material=material,
        requirements=requirements,
        serials=serials,
        workshops=workshops,
        aircraft=aircraft,
        serial_status_choices=SERIAL_STATUS_CHOICES,
        status_counts=status_counts,
        issues=issues,
    )


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
        "nivellement",
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
        "rca_rcb_reference",
    ]
    for field in string_fields:
        setattr(material, field, cleaned_value(field))

    if "category" in request.form and request.form["category"]:
        material.category = request.form["category"]

    if "workshop_id" in request.form:
        material.workshop_id = _parse_optional_int("workshop_id")

    if material.category in {"outillage", "banc d'essai"}:
        material.last_calibration_date = _parse_optional_date("last_calibration_date")
        material.calibration_expiration_date = _parse_optional_date(
            "calibration_expiration_date"
        )

    material.warranty = request.form.get("warranty") == "on"

    db.session.commit()
    flash("Fiche matériel mise à jour", "success")
    return redirect(url_for("materials.detail", material_id=material_id))


@bp.route("/<int:material_id>/serials/<int:serial_id>", methods=["POST"])
@login_required
def update_serial(material_id: int, serial_id: int):
    material = Material.query.get_or_404(material_id)
    serial = (
        MaterialSerial.query.filter_by(id=serial_id, material_id=material.id)
        .first_or_404()
    )

    serial.serial_number = _parse_optional_string("serial_number")
    status = (_parse_optional_string("status") or "stock").lower()
    if status not in {choice for choice, _ in SERIAL_STATUS_CHOICES}:
        status = "stock"
    serial.status = status
    serial.aircraft_id = _parse_optional_int("aircraft_id")
    serial.da_reference = _parse_optional_string("da_reference")
    serial.da_status = _parse_optional_string("da_status")
    serial.notes = _parse_optional_string("notes")
    serial.under_warranty = True if status == "sous_garantie" else request.form.get("under_warranty") == "on"

    if material.category == "reparable":
        material.recompute_status_counters()

    db.session.commit()
    flash("Numéro de série mis à jour", "success")
    return redirect(url_for("materials.detail", material_id=material_id))


@bp.route("/<int:material_id>/delete", methods=["POST"])
@login_required
def delete(material_id: int):
    material = Material.query.get_or_404(material_id)
    db.session.delete(material)
    db.session.commit()
    flash("Matériel supprimé", "success")
    return redirect(url_for("materials.index"))
