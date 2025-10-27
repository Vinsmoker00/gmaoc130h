from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired

from ..extensions import db
from ..models import PersonnelStatus, Role, User, Workshop

bp = Blueprint("auth", __name__, url_prefix="/auth")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])


class UserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    full_name = StringField("Full name", validators=[DataRequired()])
    rank = StringField("Rank", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    role = StringField("Role", validators=[DataRequired()])
    workshop = StringField("Workshop")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Bienvenue sur la plateforme GMAO C-130H", "success")
            return redirect(url_for("dashboard.home"))
        flash("Identifiants invalides", "danger")
    return render_template("login.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Déconnexion réussie", "info")
    return redirect(url_for("auth.login"))


@bp.route("/users", methods=["GET", "POST"])
@login_required
def manage_users():
    if current_user.role.name != "admin":
        flash("Seul l'administrateur peut gérer les comptes.", "warning")
        return redirect(url_for("dashboard.home"))

    form = UserForm()
    if form.validate_on_submit():
        role = Role.query.filter_by(name=form.role.data).first()
        workshop = None
        if form.workshop.data:
            workshop = Workshop.query.filter_by(name=form.workshop.data).first()
        if not role:
            flash("Le rôle spécifié est introuvable", "danger")
        else:
            user = User(
                username=form.username.data,
                full_name=form.full_name.data,
                rank=form.rank.data,
                role=role,
                workshop=workshop,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash("Utilisateur créé", "success")
            return redirect(url_for("auth.manage_users"))

    users = User.query.order_by(User.rank.desc()).all()
    statuses = PersonnelStatus.query.order_by(PersonnelStatus.start_date.desc()).all()
    latest_status = {}
    for record in statuses:
        latest_status.setdefault(record.personnel_id, record)
    status_options = sorted({record.status for record in statuses})
    workshops = Workshop.query.order_by(Workshop.name).all()
    return render_template(
        "personnel/index.html",
        users=users,
        manage_mode=True,
        form=form,
        statuses=statuses,
        latest_status=latest_status,
        status_options=status_options,
        status_filter=None,
        workshops=workshops,
    )
