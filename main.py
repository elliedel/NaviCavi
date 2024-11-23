from web import create_app
from flask import render_template
from flask_login import current_user

app = create_app()

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error_code=404, error_name="Page Not Found", error_message="Sorry, the page you are looking for does not exist.", user=current_user), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_code=500, error_name="Internal Server Error", error_message="Oops! Something went wrong on our end.", user=current_user), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', error_code=403, error_name="Access Forbidden", error_message="Sorry, you don't have permission to access this page.", user=current_user), 403

@app.errorhandler(401)
def unauthorized(e):
    return render_template('error.html', error_code=401, error_name="Unauthorized", error_message="You need to log in to access this page.", user=current_user), 401

if __name__ == "__main__":
    app.run(debug=True)
