from flask import Flask, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from os import path
import os
from datetime import timedelta

db = SQLAlchemy()
DB_NAME = 
mail = Mail()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = (
        
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = (
    )
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SQLALCHEMY_TRACK_NOTIFICATIONS"] = False

    app.config["MAIL_SERVER"] = 
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = 
    app.config["MAIL_PASSWORD"] = 
    app.config["MAIL_DEFAULT_SENDER"] = 

    app.config['DEBUG'] = True
    app.config['PROPAGATE_EXCEPTIONS'] = True


    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMP_IMAGE_DIR = os.path.join(BASE_DIR, 'temp_images')
    os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)

    @app.route("/favicon.ico")
    def favicon():
        return redirect(url_for("static", filename="favicon.ico"))

    mail.init_app(app)
    db.init_app(app)

    # blueprints init
    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")

    from .models import User

    create_database(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.refresh_view = "auth.login"
    login_manager.init_app(app)

    # how we log in users
    @login_manager.user_loader
    def user_loader(id):
        try:
            return User.query.get(int(id))
        except Exception as e:
            db.session.rollback()
            raise e
    
    app.config["TEMP_IMAGE_DIR"] = TEMP_IMAGE_DIR

    return app

def create_database(app):
    if not path.exists("web/" + DB_NAME):
        with app.app_context():
            db.create_all()
        print("Created Database!")
