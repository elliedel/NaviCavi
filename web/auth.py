import re, secrets, time
from sqlalchemy.exc import IntegrityError
from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user

TOKEN_EXPIRATION_TIME = 3600 # 1 hour
invite_tokens = {}

# routes
auth = Blueprint("auth", __name__)

@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("views.main", _external=True))
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash("Logged in succesfully!", category="success")
                login_user(user, remember=True)

                return redirect(url_for("views.main", _external=True))

            else:
                flash("Incorrect password.", category="error")
        else:
            flash("Email does not exist.", category="error") 

    return render_template("sign-in.html", user=current_user)


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", category="success")
    return redirect(url_for("auth.login", _external=True))

@auth.route("/forgot-password")
def forgot_password():
    return "<h1>Forgot password</h1>"


def create_invite(inviter_id):
    token = secrets.token_urlsafe(16)

    invite_tokens[token] = time.time()
    return token

@auth.route("/sign-up/<token>", methods=["GET", "POST"])
def sign_up(token):

    if token in invite_tokens:
        token_time = invite_tokens[token]


        if time.time() - token_time > TOKEN_EXPIRATION_TIME:
            flash("Invitation link has expired.", category="error")
            return redirect(url_for("auth.login", _external=True))
    else:
        flash("Invalid or expired invitation link.", category="error")
        return redirect(url_for("auth.login", _external=True))
    

    if request.method == "POST":
        email = request.form.get("email")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        existing_user = User.query.filter_by(email=email).first()

        # email regex pattern
        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        name_pattern = r"^[A-Za-z\s]+$"
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        
        if existing_user:
            flash("Email already exists.", category="error")
        if len(email) < 7:
            flash("Invalid email address.", category="error")
        elif not re.match(email_pattern, email):
            flash("Invalid email format.", category="error")
        elif len(first_name) < 2:
            flash("First name must be greater than 1 character.", category="error")
        elif not re.match(name_pattern, first_name) and not re.match(name_pattern, last_name):
            flash("Name must contain only letters.", category="error")
        elif password1 != password2:
            flash("Passwords do not match.", category="error")
        elif len(password1) < 8:
            flash("Password must be at least 8 characters long.", category="error")
        elif not re.match(password_pattern, password1):
            flash("Password must contain an uppercase letter, a lowercase letter, a number, and a special character.", category="error")
        else:
            try:

                new_user = User(
                    email=email,
                    first_name=first_name, 
                    last_name=last_name, 
                    password=generate_password_hash(password1, method="scrypt")
                    )
                db.session.add(new_user)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return "This account is already registered.", 400

            flash("Account created successfully!", category="success")
            return redirect(url_for("views.home", _external=True))

    return render_template("sign-up.html", user=current_user, token=token)