from datetime import datetime, date
from typing import Optional

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db, login_manager


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))

    users = db.relationship("User", back_populates="role", lazy="dynamic")

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"<Role {self.name}>"


class Workshop(db.Model):
    __tablename__ = "workshops"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)

    personnel = db.relationship("User", back_populates="workshop", lazy="dynamic")
    materials = db.relationship(
        "WorkshopMaterial",
        back_populates="workshop",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    visits = db.relationship("MaintenanceTask", back_populates="workshop", lazy="dynamic")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Workshop {self.name}>"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    rank = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"))
    is_active_flag = db.Column(db.Boolean, default=True)

    role = db.relationship("Role", back_populates="users")
    workshop = db.relationship("Workshop", back_populates="personnel")
    statuses = db.relationship("PersonnelStatus", back_populates="personnel", lazy="dynamic")
    assignments = db.relationship("MaintenanceTask", back_populates="lead", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self) -> bool:  # type: ignore[override]
        return self.is_active_flag

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id: str) -> Optional["User"]:
    if user_id is None:
        return None
    return User.query.get(int(user_id))


class Aircraft(db.Model):
    __tablename__ = "aircraft"

    id = db.Column(db.Integer, primary_key=True)
    tail_number = db.Column(db.String(20), unique=True, nullable=False)
    aircraft_type = db.Column(db.String(50), default="C-130H")
    location = db.Column(db.String(120))
    status = db.Column(db.String(50), default="available")
    notes = db.Column(db.Text)

    visits = db.relationship("MaintenanceVisit", back_populates="aircraft", lazy="dynamic")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Aircraft {self.tail_number}>"


class Material(db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    designation = db.Column(db.String(255), nullable=False)
    part_number = db.Column(db.String(120))
    serial_number = db.Column(db.String(120), unique=True)
    niin = db.Column(db.String(30))
    fsc = db.Column(db.String(20))
    nsn = db.Column(db.String(30))
    cage_code = db.Column(db.String(30))
    category = db.Column(db.String(40), nullable=False)
    dotation = db.Column(db.Integer, default=0)
    avionnee = db.Column(db.Integer, default=0)
    stock = db.Column(db.Integer, default=0)
    unavailable_for_repair = db.Column(db.Integer, default=0)
    in_repair = db.Column(db.Integer, default=0)
    litigation = db.Column(db.Integer, default=0)
    scrapped = db.Column(db.Integer, default=0)
    warranty = db.Column(db.Boolean, default=False)
    contract_type = db.Column(db.String(50))
    per_aircraft = db.Column(db.Integer, default=1)
    annual_consumption = db.Column(db.Integer, default=0)
    da_reference = db.Column(db.String(80))
    da_status = db.Column(db.String(80))
    consumable_stock = db.Column(db.Integer, default=0)
    consumable_dotation = db.Column(db.Integer, default=0)
    consumable_type = db.Column(db.String(80))

    workshop_links = db.relationship(
        "WorkshopMaterial",
        back_populates="material",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    requirements = db.relationship(
        "MaterialRequirement",
        back_populates="material",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    job_card_links = db.relationship(
        "JobCardMaterial",
        back_populates="material",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Material {self.designation}>"


class WorkshopMaterial(db.Model):
    __tablename__ = "workshop_materials"

    id = db.Column(db.Integer, primary_key=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    quantity = db.Column(db.Integer, default=0)

    workshop = db.relationship("Workshop", back_populates="materials")
    material = db.relationship("Material", back_populates="workshop_links")


class PersonnelStatus(db.Model):
    __tablename__ = "personnel_statuses"

    id = db.Column(db.Integer, primary_key=True)
    personnel_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(50), default="on-site")
    details = db.Column(db.String(255))
    start_date = db.Column(db.Date, default=date.today)
    end_date = db.Column(db.Date)

    personnel = db.relationship("User", back_populates="statuses")


class MaintenanceVisit(db.Model):
    __tablename__ = "maintenance_visits"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    aircraft_id = db.Column(db.Integer, db.ForeignKey("aircraft.id"), nullable=False)
    vp_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(40), default="planned")
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    description = db.Column(db.Text)

    aircraft = db.relationship("Aircraft", back_populates="visits")
    tasks = db.relationship(
        "MaintenanceTask",
        back_populates="visit",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def active_personnel(self):
        return {task.lead for task in self.tasks if task.lead is not None}


class MaintenanceTask(db.Model):
    __tablename__ = "maintenance_tasks"

    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey("maintenance_visits.id"), nullable=False)
    job_card_id = db.Column(db.Integer, db.ForeignKey("job_cards.id"))
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"))
    lead_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(40), default="pending")
    estimated_hours = db.Column(db.Float, default=0.0)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    interruption_reason = db.Column(db.String(255))
    is_package_item = db.Column(db.Boolean, default=False)
    package_code = db.Column(db.String(80))

    visit = db.relationship("MaintenanceVisit", back_populates="tasks")
    workshop = db.relationship("Workshop", back_populates="visits")
    lead = db.relationship("User", back_populates="assignments")
    job_card = db.relationship("JobCard", back_populates="tasks")
    materials = db.relationship(
        "MaterialRequirement",
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )


class MaterialRequirement(db.Model):
    __tablename__ = "material_requirements"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("maintenance_tasks.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    fulfilled = db.Column(db.Boolean, default=False)

    task = db.relationship("MaintenanceTask", back_populates="materials")
    material = db.relationship("Material", back_populates="requirements")


class JobCard(db.Model):
    __tablename__ = "job_cards"

    id = db.Column(db.Integer, primary_key=True)
    card_number = db.Column(db.String(80), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    revision = db.Column(db.String(20))
    summary = db.Column(db.Text)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    paragraphs = db.relationship(
        "JobCardParagraph",
        back_populates="job_card",
        cascade="all, delete-orphan",
        order_by="JobCardParagraph.order_index",
        lazy="joined",
    )
    steps = db.relationship(
        "JobCardStep",
        back_populates="job_card",
        cascade="all, delete-orphan",
        order_by="JobCardStep.order_index",
        lazy="joined",
    )
    substeps = db.relationship(
        "JobCardSubstep",
        back_populates="job_card",
        cascade="all, delete-orphan",
        order_by="JobCardSubstep.order_index",
        lazy="joined",
    )
    attachments = db.relationship(
        "JobCardAttachment",
        back_populates="job_card",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    tasks = db.relationship("MaintenanceTask", back_populates="job_card", lazy="dynamic")
    material_assignments = db.relationship(
        "JobCardMaterial",
        back_populates="job_card",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    @property
    def estimated_minutes(self) -> int:
        paragraph_minutes = sum(paragraph.estimated_minutes for paragraph in self.paragraphs)
        step_minutes = sum(step.estimated_minutes for step in self.steps)
        substep_minutes = sum(substep.estimated_minutes for substep in self.substeps)
        return paragraph_minutes + step_minutes + substep_minutes

    @property
    def estimated_hours(self) -> float:
        return round(self.estimated_minutes / 60.0, 2) if self.estimated_minutes else 0.0

    def root_steps(self):
        return [step for step in self.steps if step.paragraph_id is None]

    def material_summary(self):
        summary = {}
        for assignment in self.material_assignments:
            if assignment.material_id not in summary:
                summary[assignment.material_id] = {
                    "material": assignment.material,
                    "quantity": 0.0,
                }
            summary[assignment.material_id]["quantity"] += assignment.quantity or 0.0
        return summary


class JobCardAttachment(db.Model):
    __tablename__ = "job_card_attachments"

    id = db.Column(db.Integer, primary_key=True)
    job_card_id = db.Column(db.Integer, db.ForeignKey("job_cards.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255))
    file_path = db.Column(db.String(512), nullable=False, server_default="")
    mime_type = db.Column(db.String(120))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    job_card = db.relationship("JobCard", back_populates="attachments")


class JobCardParagraph(db.Model):
    __tablename__ = "job_card_paragraphs"

    id = db.Column(db.Integer, primary_key=True)
    job_card_id = db.Column(db.Integer, db.ForeignKey("job_cards.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    order_index = db.Column(db.Integer, default=0)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"))
    estimated_minutes = db.Column(db.Integer, default=0)

    job_card = db.relationship("JobCard", back_populates="paragraphs")
    workshop = db.relationship("Workshop")
    steps = db.relationship(
        "JobCardStep",
        back_populates="paragraph",
        cascade="all, delete-orphan",
        order_by="JobCardStep.order_index",
        lazy="joined",
    )
    materials = db.relationship(
        "JobCardMaterial",
        back_populates="paragraph",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )


class JobCardStep(db.Model):
    __tablename__ = "job_card_steps"

    id = db.Column(db.Integer, primary_key=True)
    job_card_id = db.Column(db.Integer, db.ForeignKey("job_cards.id"), nullable=False)
    paragraph_id = db.Column(db.Integer, db.ForeignKey("job_card_paragraphs.id"))
    title = db.Column(db.String(255))
    description = db.Column(db.Text, nullable=False)
    order_index = db.Column(db.Integer, default=0)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"))
    estimated_minutes = db.Column(db.Integer, default=0)

    job_card = db.relationship("JobCard", back_populates="steps")
    paragraph = db.relationship("JobCardParagraph", back_populates="steps")
    workshop = db.relationship("Workshop")
    substeps = db.relationship(
        "JobCardSubstep",
        back_populates="step",
        cascade="all, delete-orphan",
        order_by="JobCardSubstep.order_index",
        lazy="joined",
    )
    materials = db.relationship(
        "JobCardMaterial",
        back_populates="step",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )


class JobCardSubstep(db.Model):
    __tablename__ = "job_card_substeps"

    id = db.Column(db.Integer, primary_key=True)
    job_card_id = db.Column(db.Integer, db.ForeignKey("job_cards.id"), nullable=False)
    step_id = db.Column(db.Integer, db.ForeignKey("job_card_steps.id"), nullable=False)
    description = db.Column(db.Text, nullable=False)
    order_index = db.Column(db.Integer, default=0)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshops.id"))
    estimated_minutes = db.Column(db.Integer, default=0)

    job_card = db.relationship("JobCard", back_populates="substeps")
    step = db.relationship("JobCardStep", back_populates="substeps")
    workshop = db.relationship("Workshop")
    materials = db.relationship(
        "JobCardMaterial",
        back_populates="substep",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )


class JobCardMaterial(db.Model):
    __tablename__ = "job_card_materials"

    id = db.Column(db.Integer, primary_key=True)
    job_card_id = db.Column(db.Integer, db.ForeignKey("job_cards.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    paragraph_id = db.Column(db.Integer, db.ForeignKey("job_card_paragraphs.id"))
    step_id = db.Column(db.Integer, db.ForeignKey("job_card_steps.id"))
    substep_id = db.Column(db.Integer, db.ForeignKey("job_card_substeps.id"))
    quantity = db.Column(db.Float, default=1.0)
    notes = db.Column(db.String(255))

    job_card = db.relationship("JobCard", back_populates="material_assignments")
    material = db.relationship("Material", back_populates="job_card_links")
    paragraph = db.relationship("JobCardParagraph", back_populates="materials")
    step = db.relationship("JobCardStep", back_populates="materials")
    substep = db.relationship("JobCardSubstep", back_populates="materials")


class InventorySnapshot(db.Model):
    __tablename__ = "inventory_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    taken_at = db.Column(db.DateTime, default=datetime.utcnow)
    available = db.Column(db.Integer, nullable=False)
    reserved = db.Column(db.Integer, default=0)
    consumption_window_days = db.Column(db.Integer, default=30)

    material = db.relationship("Material")


class DemandPrediction(db.Model):
    __tablename__ = "demand_predictions"

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    window_days = db.Column(db.Integer, default=30)
    predicted_need = db.Column(db.Float, nullable=False)
    model = db.Column(db.String(80), default="wilson")

    material = db.relationship("Material")
