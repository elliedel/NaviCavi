from flask import Blueprint, render_template, request, flash,Response, redirect, url_for, session, send_file
from flask_login import login_required, current_user
from flask_mail import Message 
from sqlalchemy import func
from werkzeug.utils import secure_filename
from .models import Result, UploadedImage, Flag
from .yolo_models import process_image
from . import db, mail
from .auth import create_invite
import os
import tempfile
from datetime import datetime

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

views = Blueprint("views", __name__)

@views.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("views.main", _external=True))
    else:
        return render_template("index.html", user=current_user)


@views.route("/about")
def about():
    return render_template("about.html", user=current_user)

@views.route("/terms-and-conditions")
def terms():
    return render_template("terms.html", user=current_user)

@views.route("/privacy-policy")
def policies():
    return render_template("policies.html", user=current_user)

@views.route("/help")
def help():
    return render_template("help.html", user=current_user)

''' 
AUTHENTICATED STATE
'''
@views.route("/main", methods=["GET", "POST"])
@login_required

def main():
    if current_user.is_authenticated:
        invite_url = None
        if current_user.id == 1:

            token = create_invite(current_user.id)
            invite_url = url_for('auth.sign_up', token=token, _external=True)
        
        latest_image = None
        raw_image_path = None
        annotated_is_image_path = None
        caries_info = None

        uploaded_image_id = session.pop('uploaded_image_id', None)
        if uploaded_image_id:
            latest_image = UploadedImage.query.filter_by(id=uploaded_image_id).first() if uploaded_image_id else None 

            if latest_image:
                raw_image_path = f"raw_{latest_image.id}.jpg"
                annotated_is_image_path = f"annotated_is_{latest_image.id}.jpg"

            temp_image = session.get("temp_image")
            if temp_image:
                caries_info = temp_image.get("caries_info")

        return render_template(
            "main.html", user=current_user,
            latest_image=latest_image, raw_image_path=raw_image_path,
            annotated_is_image_path=annotated_is_image_path,
            caries_info=caries_info,
            invite_url=invite_url
        )
    else:
        return render_template("index.html", user=current_user)

@views.route("/gallery")
@login_required

def gallery():
    page = request.args.get("page", 1, type=int)
    per_page = 9
    gallery_images = Result.query.filter_by(user_id=current_user.id).paginate(page=page, per_page=per_page)
    return render_template("gallery.html", user=current_user, gallery_images=gallery_images)

@views.route("/gallery/result/<int:id>")
@login_required

def gallery_image(id):
    display_img_result = Result.query.filter_by(id=id, user_id=current_user.id).first()
    if display_img_result:
        return render_template("gallery_image.html", user=current_user, display_img_result=display_img_result)
    else:
        flash("Image not found.", category="error")
        return redirect(url_for("views.gallery", _external=True))
    
@views.route("/upload", methods=["POST"])
@login_required

def upload():
    img_upload = request.files.get("img_upload")
    upload_consent = request.form.get("upload_consent")

    if not img_upload:
        flash("No image uploaded", category="error")
        return redirect(url_for("views.main", _external=True))

    filename = secure_filename(img_upload.filename)
    mimetype = img_upload.mimetype

    if not allowed_file(filename):
        flash("Only JPG, JPEG, and PNG files are allowed!", category="error")
        return redirect(url_for("views.main", _external=True))

    if not filename or not mimetype:
        flash("Bad upload", category="error")
        return redirect(url_for("views.main", _external=True))
    
    temp_file_path = os.path.join(tempfile.gettempdir(), filename)
    img_upload.save(temp_file_path)

    raw_path, annotated_is_path, caries_info = process_image(temp_file_path)

    if all([raw_path and annotated_is_path]):
        if upload_consent:
            new_filename = get_unique_filename(filename, current_user.id)
            try:
                with open(annotated_is_path, "rb") as f:
                    image_data = f.read()
                
                image_path = UploadedImage(
                    image_path=image_data,
                    name=new_filename,
                    mimetype=mimetype,
                    user_id=current_user.id,
                )
                db.session.add(image_path)
                db.session.commit()
                session["uploaded_image_id"] = image_path.id

                annotated_is_unique_path = os.path.join(tempfile.gettempdir(), f"annotated_is_{image_path.id}.jpg")

                os.rename(raw_path, os.path.join(tempfile.gettempdir(), f"raw_{image_path.id}.jpg"))
                os.rename(annotated_is_path, annotated_is_unique_path)
                
                session["temp_image"] = {
                    "annotated_is_unique_path": annotated_is_unique_path,
                    "mimetype": mimetype,
                    "caries_info": caries_info,
                    "uploaded_image_id": image_path.id
                }
                flash("Image uploaded, processed, and saved successfully!", category="success")
            except Exception as e:
                db.session.rollback()
                flash(f"An error occurred: {str(e)}", category="error")
        else:
            # store processed image paths and mimetype in session
            session["temp_image"] = {
                "filename": filename,
                "annotated_is_path": annotated_is_path,
                "mimetype": mimetype,
                "caries_info": caries_info,
                "uploaded_image_id": None
            }
            flash("Image uploaded and processed but not saved due to missing consent.", category="info")
    else:
        flash("Error processing the image.", category="error")
    
    return redirect(url_for("views.main", _external=True))


@views.route("/confirm_processed_image", methods=["GET","POST"])
@login_required
def confirm_processed_image():
    temp_image = session.get("temp_image")
    patient_name = request.form.get("patient_name") or " "
    processed_image_consent = request.form.get("result_consent")
    rating = request.form.get("rating")

    if not temp_image:
        flash("No image found to save.", category="error")
        return redirect(url_for("views.main", _external=True))

    if processed_image_consent and patient_name:
        annotated_is_unique_path = temp_image.get("annotated_is_unique_path")
        mimetype = temp_image["mimetype"]
        uploaded_image_id = temp_image.get("uploaded_image_id")

        try:
            with open(annotated_is_unique_path, "rb") as f:
                processed_image_data = f.read()
            
            today_date = datetime.now().strftime("%Y%m%d")
            today_images_count = Result.query.filter(
                db.func.date(Result.result_date) == db.func.date(func.now())
            ).count()

            image_name = f"{today_date}_{today_images_count + 1}"            

            result_entry = Result(
                image_path=processed_image_data,
                name=image_name,
                mimetype=mimetype,
                patient_name=patient_name,
                result_date=func.now(),
                user_id=current_user.id,
                uploaded_image_id=uploaded_image_id
            )
            db.session.add(result_entry)
            db.session.commit()

            if rating:
                flag_entry = Flag(
                    reason=rating,
                    user_id=current_user.id,
                    result_id=result_entry.id 
                )
                db.session.add(flag_entry)
                db.session.commit()

            flash("Processed image and details saved successfully!", category="success")
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {str(e)}", category="error")

    return redirect(url_for("views.main", _external=True))

'''
PURE PROCESS
'''
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@views.route("/<int:id>")
@login_required
def get_img(id):
    img_upload = UploadedImage.query.filter_by(id=id, user_id=current_user.id).first()
    
    if not img_upload:
        return 'Image Not Found!', 404

    return Response(
        img_upload.image_path,
        mimetype=img_upload.mimetype
    )

@views.route("/serve_image/<path:filename>")
@login_required
def serve_image(filename):
    try:
        return send_file(
            os.path.join(tempfile.gettempdir(), filename), mimetype="image/jpeg"
        )
    except Exception as e:
        print(f"Error serving image: {e}")
        return "Error serving image", 500

@views.route("/serve_gallery_image/<int:id>")
@login_required
def serve_gallery_image(id):
    image_result = Result.query.filter_by(id=id).first()

    if not image_result:
        return "Image not found", 404

    try:
        return Response(
            image_result.image_path,
            mimetype=image_result.mimetype
        )
    except Exception as e:
        print(f"Error serving image: {e}")
        return "Error serving image", 500


def get_unique_filename(filename, user_id): 
    base, ext = os.path.splitext(filename)
    counter = 1

    while UploadedImage.query.filter_by(name=filename, user_id=user_id).first() is not None:
        filename = f"{base}({counter}){ext}"
        counter += 1

    return filename

@views.route("/delete_image/<int:id>", methods=["POST"])
@login_required
def delete_image(id):

    image_to_delete = Result.query.filter_by(id=id, user_id=current_user.id).first()

    if not image_to_delete:
        flash("Image not found", category="error")
        return redirect(url_for("views.gallery", _external=True))

    try:
        related_flags = Flag.query.filter_by(result_id=image_to_delete.id).all()

        for flag in related_flags:
            db.session.delete(flag)

        for flag in related_flags:
            flag.result_id = None

        file_path = os.path.join(tempfile.gettempdir(), f"raw_{image_to_delete.id}.jpg")
        if os.path.exists(file_path):
            os.remove(file_path)

        db.session.delete(image_to_delete)
        db.session.commit()

        flash("Image deleted successfully!", category="success")

    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while deleting the image: {str(e)}", category="error")

    return redirect(url_for("views.gallery", _external=True))



@views.route("/submit_contact_form", methods=["POST"])
def submit_contact_form():

    contact_name = request.form.get("contact_name")
    contact_email = request.form.get("contact_email")
    contact_subject = request.form.get("contact_subject")
    message = request.form.get("message")

    try:
        msg = Message(subject=f"NaviCavi Contact Form Submission: {contact_subject}",
                      sender=contact_email,
                      recipients=["ellegdlcrz@gmail.com"])
        
        message_body = f"""
        New contact form submission from NaviCavi:

        Name: {contact_name}
        Email: {contact_email}
        Subject: {contact_subject}

        Message:
        {message}

        Best regards,
        NaviCavi Team
        """
        msg.body = message_body
        mail.send(msg)
        flash("Message sent successfully!", "success")
    except Exception as e:
        flash(f"Failed to send message: {str(e)}", "danger")

    return redirect(url_for("views.about", _external=True))