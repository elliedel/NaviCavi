from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func

class Invite(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    token = db.Column(db.String(32), unique=True)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())


class UploadedImage(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    image_path = db.Column(db.LargeBinary, nullable=False)
    name = db.Column(db.Text, nullable=False, unique=True)
    mimetype = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    results = db.relationship('Result', backref='uploaded_image', cascade="all, delete", lazy=True)
    
class Result(db.Model): # processed image
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    image_path = db.Column(db.LargeBinary, unique=False, nullable=False)
    name = db.Column(db.Text, nullable=False, unique=True)
    mimetype = db.Column(db.Text, nullable=False)
    patient_name = db.Column(db.String(150))
    result_date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    flags = db.relationship('Flag', backref='result', cascade="all, delete", lazy=True)
    uploaded_image_id = db.Column(db.Integer, db.ForeignKey('uploaded_image.id'), nullable=False)


class Flag(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    result_id = db.Column(db.Integer, db.ForeignKey('result.id'), nullable=True)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(50))
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    invitation_token = db.Column(db.String(100), unique=True, nullable=True)

    uploaded_image = db.relationship('UploadedImage', backref='user', lazy=True)
    results = db.relationship('Result', backref='user', lazy=True)