from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from PIL import Image
import qrcode
import io
import base64
import os
import cloudinary
import cloudinary.uploader
from datetime import datetime, timedelta

# =========================================================
# APP CONFIG
# =========================================================
app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET_KEY"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///employees.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

db = SQLAlchemy(app)

# =========================================================
# CLOUDINARY CONFIG
# =========================================================
cloudinary.config(
    cloud_name="dr6bskpxy",
    api_key="854213433653329",
    api_secret="x7Ak24biA-hPhm66C3tYBrlW_4Y"
)

# =========================================================
# DATABASE MODELS
# =========================================================
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)


class Employee(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    gender = db.Column(db.String(10), nullable=False)

    blood_group = db.Column(db.String(10), nullable=False)
    contact_person_name = db.Column(db.String(100), nullable=False)
    relation = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    company_phone_number = db.Column(db.String(20), nullable=False)

    qr_url = db.Column(db.Text)
    qr_base64 = db.Column(db.Text)

# =========================================================
# LOGIN REQUIRED DECORATOR
# =========================================================
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin_login"))
        session.permanent = True
        return func(*args, **kwargs)
    return wrapper

# =========================================================
# QR CODE GENERATOR
# =========================================================
def generate_qr_code(employee_id, logo_path="static/images/company_logo.jpg"):
    qr_data = f"{request.host_url}employee/{employee_id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        size = qr_img.size[0] // 4
        logo = logo.resize((size, size), Image.Resampling.LANCZOS)
        pos = ((qr_img.size[0] - size) // 2, (qr_img.size[1] - size) // 2)
        qr_img.paste(logo, pos)

    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    buffer.seek(0)

    qr_base64 = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

    buffer.seek(0)
    upload = cloudinary.uploader.upload(
        buffer,
        folder="employee_qrcodes",
        public_id=employee_id,
        overwrite=True
    )

    return upload["secure_url"], qr_base64

# =========================================================
# DATE FORMAT FILTER
# =========================================================
@app.template_filter("datetimeformat")
def datetimeformat(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return value

# =========================================================
# ADMIN AUTH
# =========================================================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        admin = Admin.query.filter_by(username=request.form["username"]).first()
        if admin and check_password_hash(admin.password_hash, request.form["password"]):
            session["admin_id"] = admin.id
            return redirect(url_for("index"))
        error = "Invalid username or password"
    return render_template("admin_login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

# =========================================================
# CHANGE PASSWORD
# =========================================================
@app.route("/admin/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    admin = Admin.query.get(session["admin_id"])
    error = success = None

    if request.method == "POST":
        if not check_password_hash(admin.password_hash, request.form["current_password"]):
            error = "Current password incorrect"
        elif request.form["new_password"] != request.form["confirm_password"]:
            error = "Passwords do not match"
        else:
            admin.password_hash = generate_password_hash(request.form["new_password"])
            db.session.commit()
            success = "Password updated successfully"

    return render_template("change_password.html", error=error, success=success)

# =========================================================
# ADMIN MANAGEMENT (MULTIPLE ADMINS)
# =========================================================
@app.route("/admin/manage", methods=["GET", "POST"])
@login_required
def manage_admins():
    error = success = None

    if request.method == "POST":
        if Admin.query.filter_by(username=request.form["username"]).first():
            error = "Username already exists"
        else:
            admin = Admin(
                username=request.form["username"],
                password_hash=generate_password_hash(request.form["password"])
            )
            db.session.add(admin)
            db.session.commit()
            success = "Admin created successfully"

    admins = Admin.query.all()
    return render_template(
        "manage_admins.html",
        admins=admins,
        error=error,
        success=success
    )


@app.route("/admin/delete/<int:admin_id>", methods=["POST"])
@login_required
def delete_admin(admin_id):
    if admin_id != session["admin_id"]:
        admin = Admin.query.get_or_404(admin_id)
        db.session.delete(admin)
        db.session.commit()
    return redirect(url_for("manage_admins"))

# =========================================================
# EMPLOYEE ROUTES
# =========================================================
@app.route("/")
@login_required
def index():
    employees = Employee.query.all()
    return render_template("index.html", employees=employees)


@app.route("/add", methods=["GET", "POST"])
@login_required
def add_employee_page():
    message = None
    if request.method == "POST":
        if Employee.query.get(request.form["employee_id"]):
            message = "Employee ID already exists!"
        else:
            qr_url, qr_base64 = generate_qr_code(request.form["employee_id"])
            emp = Employee(
                id=request.form["employee_id"],
                name=request.form["name"],
                dob=request.form["dob"],
                gender=request.form["gender"],
                blood_group=request.form["blood_group"],
                contact_person_name=request.form["contact_person_name"],
                relation=request.form["relation"],
                phone_number=request.form["phone_number"],
                company_phone_number=request.form["company_phone_number"],
                qr_url=qr_url,
                qr_base64=qr_base64
            )
            db.session.add(emp)
            db.session.commit()
            message = "Employee added successfully"
    return render_template("add_employee_form.html", message=message)


@app.route("/edit/<employee_id>", methods=["GET", "POST"])
@login_required
def edit_employee(employee_id):
    emp = Employee.query.get_or_404(employee_id)
    message = None

    if request.method == "POST":
        emp.name = request.form["name"]
        emp.dob = request.form["dob"]
        emp.gender = request.form["gender"]
        emp.blood_group = request.form["blood_group"]
        emp.contact_person_name = request.form["contact_person_name"]
        emp.relation = request.form["relation"]
        emp.phone_number = request.form["phone_number"]
        emp.company_phone_number = request.form["company_phone_number"]
        db.session.commit()
        message = "Employee updated successfully"

    return render_template("edit_employee.html", employee=emp, message=message)


@app.route("/delete/<employee_id>", methods=["POST"])
@login_required
def delete_employee(employee_id):
    emp = Employee.query.get(employee_id)
    if emp:
        db.session.delete(emp)
        db.session.commit()
    return redirect(url_for("index"))

# =========================================================
# PUBLIC EMERGENCY PAGE (NO LOGIN)
# =========================================================
@app.route("/employee/<employee_id>")
def emergency_details_page(employee_id):
    emp = Employee.query.get_or_404(employee_id)
    return render_template("emergency_details.html", employee=emp)

# =========================================================
# SEARCH
# =========================================================
@app.route("/edit_employee_search", methods=["GET", "POST"])
@login_required
def edit_employee_search():
    error_message = None
    if request.method == "POST":
        emp = Employee.query.get(request.form["employee_id"])
        if emp:
            return redirect(url_for("edit_employee", employee_id=emp.id))
        error_message = "Employee not found"
    return render_template("edit_employee_search.html", error_message=error_message)

# =========================================================
# INIT
# =========================================================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # Default admin
        if not Admin.query.filter_by(username="admin").first():
            admin = Admin(
                username="admin",
                password_hash=generate_password_hash("admin123")
            )
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True)
