from math import sqrt
from statistics import mean

from flask import Blueprint, render_template, request
from flask_login import login_required

from ..extensions import db
from ..models import DemandPrediction, InventorySnapshot, Material

bp = Blueprint("analytics", __name__, url_prefix="/analytics")


def wilson_eoq(demand_rate: float, order_cost: float = 1.0, holding_cost: float = 0.5) -> float:
    if demand_rate <= 0:
        return 0
    return sqrt((2 * demand_rate * order_cost) / holding_cost)


@bp.route("/predictions")
@login_required
def predictions():
    window = request.args.get("window", type=int, default=30)
    materials = Material.query.order_by(Material.designation).all()
    results = []
    for material in materials:
        snapshots = (
            InventorySnapshot.query.filter_by(material_id=material.id)
            .order_by(InventorySnapshot.taken_at.desc())
            .limit(6)
            .all()
        )
        consumption_rates = []
        for snapshot in snapshots:
            if snapshot.consumption_window_days:
                consumption_rates.append(snapshot.reserved / snapshot.consumption_window_days)
        avg_rate = mean(consumption_rates) if consumption_rates else material.annual_consumption / 365 or 0
        predicted_need = wilson_eoq(avg_rate * window, order_cost=1.5, holding_cost=0.7)
        record = DemandPrediction.query.filter_by(material_id=material.id, window_days=window).first()
        if record:
            record.predicted_need = predicted_need
        else:
            record = DemandPrediction(material=material, window_days=window, predicted_need=predicted_need)
            db.session.add(record)
        results.append((material, predicted_need, snapshots))

    db.session.commit()
    return render_template("analytics/predictions.html", results=results, window=window)
