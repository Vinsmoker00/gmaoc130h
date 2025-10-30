from __future__ import annotations

from pathlib import Path
from typing import Optional

from flask import Flask

from .config import BaseConfig
from .extensions import db, login_manager
from .models import Role, Workshop, User


def create_app(config_class: Optional[type] = None) -> Flask:
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )

    app.config.from_object(config_class or BaseConfig)

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_seed_data()
        from .utils.seed import populate_demo_data

        populate_demo_data(skip_if_exists=True)

    register_blueprints(app)
    register_cli(app)

    @app.context_processor
    def inject_nav_links():
        return {
            "nav_links": [
                ("Accueil", "dashboard.landing"),
                ("Tableau de bord", "dashboard.home"),
                ("Flotte", "aircrafts.index"),
                ("Matériels", "materials.index"),
                ("Ateliers", "workshops.index"),
                ("Personnel", "personnel.index"),
                ("Visites", "maintenance.index"),
                ("Gantt", "gantt.index"),
                ("Archive", "archive.index"),
                ("Prédictions", "analytics.predictions"),
            ]
        }

    return app


def register_blueprints(app: Flask) -> None:
    from .auth.routes import bp as auth_bp
    from .dashboard.routes import bp as dashboard_bp
    from .aircrafts.routes import bp as aircrafts_bp
    from .materials.routes import bp as materials_bp
    from .workshops.routes import bp as workshops_bp
    from .personnel.routes import bp as personnel_bp
    from .maintenance.routes import bp as maintenance_bp
    from .archive.routes import bp as archive_bp
    from .analytics.routes import bp as analytics_bp
    from .gantt.routes import bp as gantt_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(aircrafts_bp)
    app.register_blueprint(materials_bp)
    app.register_blueprint(workshops_bp)
    app.register_blueprint(personnel_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(archive_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(gantt_bp)


def register_cli(app: Flask) -> None:
    from .utils.seed import register_seed_commands

    register_seed_commands(app)


def ensure_seed_data() -> None:
    if Role.query.count() == 0:
        db.session.add(Role(name="admin", description="Full platform access"))
        db.session.add(Role(name="engineer", description="Engineering officer"))
        db.session.add(Role(name="technician", description="Maintenance technician"))

    if Workshop.query.count() == 0:
        workshops = [
            "MOTEUR",
            "EQT/BORD",
            "RADIO",
            "APG",
            "HELICE",
            "FUEL",
            "CHAUD",
            "MARS",
            "S/S",
            "DRS",
            "NDI",
        ]
        for name in workshops:
            db.session.add(Workshop(name=name))

    if User.query.count() == 0:
        admin_role = Role.query.filter_by(name="admin").first()
        assert admin_role is not None
        user = User(username="admin", full_name="Admin", rank="CPT", role=admin_role)
        user.set_password("admin123")
        db.session.add(user)

    db.session.commit()
