from flask import Blueprint
from .models import User
from werkzeug.security import generate_password_hash
from . import db
admin = Blueprint("auth", __name__)

def create_first_user():

    if User.query.filter_by(email="[INSERT_EMAIL_HERE]").first():
        print("Admin user already exists.")
        return
    

    new_user = User(
        email="[INSERT_EMAIL_HERE]",
        first_name="[INSERT_FNAME_HERE]",
        last_name="[INSERT_LNAME_HERE]",
        password=generate_password_hash("[INSERT_PASSWORD_HERE]", method="scrypt")
    )

    # Add the new user to the session and commit
    db.session.add(new_user)
    db.session.commit()
    print("Admin user created successfully.")