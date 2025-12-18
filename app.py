import os
import io
import base64
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from PIL import Image
import qrcode
import cloudinary
import cloudinary.uploader

from dotenv import load_dotenv

# =========================================================
# LOAD ENV
# =========================================================
load_dotenv()

# =========================================================
# APP CONFIG
# =========================================================
app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

# =========================================================
# DATABASE CONFIG (PostgreSQL / Render)
# =========================================================
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# Fix deprecated postgres:// prefix
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================================================
# CLOUDINARY CONFIG
# =========================================================
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

# =========================================================
# DATABASE MODELS
# =========================================================
class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)


class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.String(10), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    blood_group = db.Column(db.String(10), nullable=False)
    contact_person_name = db.Column(db.String(100), nullable=False)
    relation = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    company_phone_number = db.Column(db.String(20), nullable=False)
    qr_url = db.Column(db.Text)
    qr_base64 = db.Column(db.Text)

# =========================================================
# AUTH DECORATOR
# =========================================================
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin_login"))
        session.permanent = True
        return fn(*args, **kwargs)
    return wrapper

# =========================================================
# QR CODE GENERATOR
# =========================================================
def generate_qr_code(employee_id):
    qr_data = f"{request.host_url}employee/{employee_id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    logo_path = "static/images/company_logo.jpg"
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        size = qr_img.size[0] // 4
        logo = logo.resize((size, size), Image.Resampling.LANCZOS)
        pos = ((qr_img.size[0] - size) // 2, (qr_img.size[1] - size) // 2)
        qr_img.paste(logo, pos)

    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    buffer.seek(0)

    qr_base64 = "data:image/png;base64," + base64.b64encode(buffer.read()).decode()

    buffer.seek(0)
    upload = cloudinary.uploader.upload(
        buffer,
        folder="employee_qrcodes",
        public_id=employee_id,
        overwrite=True,
    )

    return upload["secure_url"], qr_base64

# =========================================================
# TEMPLATE FILTER
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
# FORGOT PASSWORD
# =========================================================
@app.route("/admin/forgot-password", methods=["GET", "POST"])
def forgot_password():
    error = success = None

    if request.method == "POST":
        admin = Admin.query.filter_by(username=request.form["username"]).first()

        if not admin:
            error = "Admin not found"
        elif request.form["new_password"] != request.form["confirm_password"]:
            error = "Passwords do not match"
        else:
            admin.password_hash = generate_password_hash(request.form["new_password"])
            db.session.commit()
            success = "Password reset successful"

    return render_template("forgot_password.html", error=error, success=success)

# =========================================================
# CHANGE PASSWORD
# =========================================================
@app.route("/admin/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    admin = db.session.get(Admin, session["admin_id"])
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
# ADMIN MANAGEMENT
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
                password_hash=generate_password_hash(request.form["password"]),
            )
            db.session.add(admin)
            db.session.commit()
            success = "Admin created"

    admins = Admin.query.all()
    return render_template("manage_admins.html", admins=admins, error=error, success=success)


@app.route("/admin/delete/<int:admin_id>", methods=["POST"])
@login_required
def delete_admin(admin_id):
    if admin_id != session["admin_id"]:
        admin = db.session.get(Admin, admin_id)
        if admin:
            db.session.delete(admin)
            db.session.commit()
    return redirect(url_for("manage_admins"))

# =========================================================
# EMPLOYEES
# =========================================================
@app.route("/")
@login_required
def index():
    return render_template("index.html", employees=Employee.query.all())


@app.route("/add", methods=["GET", "POST"])
@login_required
def add_employee_page():
    message = None

    if request.method == "POST":
        if db.session.get(Employee, request.form["employee_id"]):
            message = "Employee ID already exists"
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
                qr_base64=qr_base64,
            )
            db.session.add(emp)
            db.session.commit()
            message = "Employee added successfully"

    return render_template("add_employee_form.html", message=message)


@app.route("/edit/<employee_id>", methods=["GET", "POST"])
@login_required
def edit_employee(employee_id):
    emp = db.session.get(Employee, employee_id)
    if not emp:
        return redirect(url_for("index"))

    if request.method == "POST":
        for field in [
            "name", "dob", "gender", "blood_group",
            "contact_person_name", "relation",
            "phone_number", "company_phone_number"
        ]:
            setattr(emp, field, request.form[field])
        db.session.commit()

    return render_template("edit_employee.html", employee=emp)


@app.route("/delete/<employee_id>", methods=["POST"])
@login_required
def delete_employee(employee_id):
    emp = db.session.get(Employee, employee_id)
    if emp:
        db.session.delete(emp)
        db.session.commit()
    return redirect(url_for("index"))

# =========================================================
# PUBLIC EMERGENCY PAGE
# =========================================================
@app.route("/employee/<employee_id>")
def emergency_details_page(employee_id):
    emp = db.session.get(Employee, employee_id)
    if not emp:
        return "Not found", 404
    return render_template("emergency_details.html", employee=emp)

# =========================================================
# INIT
# =========================================================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        if not Admin.query.filter_by(username="admin").first():
            db.session.add(
                Admin(
                    username="admin",
                    password_hash=generate_password_hash("admin123"),
                )
            )
            db.session.commit()

    app.run(debug=True)
