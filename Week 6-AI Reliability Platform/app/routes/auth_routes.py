from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from app import bcrypt
from app.models.models import db, User
from app.services.log_service import log_event

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("workspace.list_workspaces"))
    return render_template("index.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("workspace.list_workspaces"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        errors = []
        if len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if "@" not in email:
            errors.append("Please enter a valid email address.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if User.query.filter_by(username=username).first():
            errors.append("That username is already taken.")
        if User.query.filter_by(email=email).first():
            errors.append("That email is already registered.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", username=username, email=email)

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        log_event("auth", f"New user registered: {username}", user_id=user.id)

        login_user(user)
        flash(f"Welcome, {username}! Your account has been created.", "success")
        return redirect(url_for("workspace.list_workspaces"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("workspace.list_workspaces"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if user and user.check_password(password):
            user.last_login_at = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=True)
            log_event("auth", f"User logged in: {user.username}", user_id=user.id)
            flash(f"Welcome back, {user.username}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("workspace.list_workspaces"))

        flash("Invalid username/email or password.", "error")
        return render_template("login.html", identifier=identifier)

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    log_event("auth", f"User logged out: {current_user.username}", user_id=current_user.id)
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.index"))
