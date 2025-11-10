from __future__ import annotations

from pathlib import Path
from typing import Optional

from flask import Flask
from sqlalchemy import inspect, text

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
        apply_schema_upgrades()
        db.create_all()
        ensure_seed_data()

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


def apply_schema_upgrades() -> None:
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    executed_any_statement = False

    if "job_card_attachments" in table_names:
        columns = {column["name"] for column in inspector.get_columns("job_card_attachments")}
        statements = []
        added_file_path = False

        if "file_path" not in columns:
            statements.append(
                text(
                    "ALTER TABLE job_card_attachments ADD COLUMN file_path VARCHAR(512) NOT NULL DEFAULT '';"
                )
            )
            added_file_path = True

        if "mime_type" not in columns:
            statements.append(text("ALTER TABLE job_card_attachments ADD COLUMN mime_type VARCHAR(120);"))

        for statement in statements:
            db.session.execute(statement)
            executed_any_statement = True

        if added_file_path:
            db.session.execute(
                text("UPDATE job_card_attachments SET file_path = filename WHERE file_path = '';"),
            )
            executed_any_statement = True

    if "maintenance_tasks" in table_names:
        columns = {column["name"] for column in inspector.get_columns("maintenance_tasks")}
        statements = []

        if "is_package_item" not in columns:
            statements.append(
                text(
                    "ALTER TABLE maintenance_tasks ADD COLUMN is_package_item BOOLEAN NOT NULL DEFAULT 0;"
                )
            )

        if "package_code" not in columns:
            statements.append(text("ALTER TABLE maintenance_tasks ADD COLUMN package_code VARCHAR(80);"))

        for statement in statements:
            db.session.execute(statement)
            executed_any_statement = True

    if "materials" in table_names:
        columns = {column["name"] for column in inspector.get_columns("materials")}
        statements = []

        def add_material_column(name: str, ddl: str) -> None:
            if name not in columns:
                statements.append(text(f"ALTER TABLE materials ADD COLUMN {ddl};"))

        add_material_column("part_number", "part_number VARCHAR(120)")
        add_material_column("serial_number", "serial_number VARCHAR(120) UNIQUE")
        add_material_column("niin", "niin VARCHAR(30)")
        add_material_column("fsc", "fsc VARCHAR(20)")
        add_material_column("nsn", "nsn VARCHAR(30)")
        add_material_column("cage_code", "cage_code VARCHAR(30)")
        add_material_column(
            "category",
            "category VARCHAR(40) NOT NULL DEFAULT 'reparable'",
        )
        add_material_column("dotation", "dotation INTEGER NOT NULL DEFAULT 0")
        add_material_column("avionnee", "avionnee INTEGER NOT NULL DEFAULT 0")
        add_material_column("stock", "stock INTEGER NOT NULL DEFAULT 0")
        add_material_column(
            "unavailable_for_repair",
            "unavailable_for_repair INTEGER NOT NULL DEFAULT 0",
        )
        add_material_column("in_repair", "in_repair INTEGER NOT NULL DEFAULT 0")
        add_material_column("litigation", "litigation INTEGER NOT NULL DEFAULT 0")
        add_material_column("scrapped", "scrapped INTEGER NOT NULL DEFAULT 0")
        add_material_column("warranty", "warranty BOOLEAN NOT NULL DEFAULT 0")
        add_material_column("contract_type", "contract_type VARCHAR(50)")
        add_material_column("per_aircraft", "per_aircraft INTEGER NOT NULL DEFAULT 1")
        add_material_column(
            "annual_consumption",
            "annual_consumption INTEGER NOT NULL DEFAULT 0",
        )
        add_material_column("da_reference", "da_reference VARCHAR(80)")
        add_material_column("da_status", "da_status VARCHAR(80)")
        add_material_column(
            "consumable_stock",
            "consumable_stock INTEGER NOT NULL DEFAULT 0",
        )
        add_material_column(
            "consumable_dotation",
            "consumable_dotation INTEGER NOT NULL DEFAULT 0",
        )
        add_material_column("consumable_type", "consumable_type VARCHAR(80)")
        add_material_column("nivellement", "nivellement INTEGER NOT NULL DEFAULT 0")
        add_material_column("rca_rcb_reference", "rca_rcb_reference VARCHAR(120)")
        add_material_column("last_calibration_date", "last_calibration_date DATE")
        add_material_column(
            "calibration_expiration_date",
            "calibration_expiration_date DATE",
        )
        add_material_column("workshop_id", "workshop_id INTEGER REFERENCES workshops(id)")

        for statement in statements:
            db.session.execute(statement)
            executed_any_statement = True

        if "category" not in columns and statements:
            db.session.execute(
                text(
                    "UPDATE materials SET category = 'reparable' WHERE category IS NULL OR TRIM(category) = '';"
                )
            )
            executed_any_statement = True

    if "job_cards" in table_names:
        columns = {column["name"] for column in inspector.get_columns("job_cards")}
        statements = []
        added_title = False
        added_created_at = False

        if "title" not in columns:
            statements.append(text("ALTER TABLE job_cards ADD COLUMN title VARCHAR(255) NOT NULL DEFAULT '';"))
            added_title = True

        if "revision" not in columns:
            statements.append(text("ALTER TABLE job_cards ADD COLUMN revision VARCHAR(20);"))

        if "summary" not in columns:
            statements.append(text("ALTER TABLE job_cards ADD COLUMN summary TEXT;"))

        if "content" not in columns:
            statements.append(text("ALTER TABLE job_cards ADD COLUMN content TEXT;"))

        if "created_at" not in columns:
            statements.append(text("ALTER TABLE job_cards ADD COLUMN created_at DATETIME;"))
            added_created_at = True

        for statement in statements:
            db.session.execute(statement)
            executed_any_statement = True

        if added_title:
            db.session.execute(
                text(
                    "UPDATE job_cards SET title = CASE WHEN title = '' THEN COALESCE(card_number, 'Job card') ELSE title END;"
                )
            )
            executed_any_statement = True

        if added_created_at:
            db.session.execute(
                text(
                    "UPDATE job_cards SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP);"
                )
            )
            executed_any_statement = True

    if executed_any_statement:
        db.session.commit()


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
