from flask import Flask, render_template, request, redirect, url_for
import json
from PIL import Image
import qrcode
import io
import base64
import os
import cloudinary
import cloudinary.uploader
from datetime import datetime

app = Flask(__name__)

# ---------------- Cloudinary Configuration ----------------
cloudinary.config(
    cloud_name="dr6bskpxy",
    api_key="854213433653329",
    api_secret="x7Ak24biA-hPhm66C3tYBrlW_4Y"
)

# In-memory storage
employees = {}

# ---------------- QR Code Generator ----------------
def generate_qr_code(employee_id, name, logo_path="static/images/company_logo.jpg"):
    data = f"{request.host_url}employee/{employee_id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # Add logo if exists
    if logo_path and os.path.exists(logo_path):
        logo = Image.open(logo_path)
        qr_width, qr_height = qr_img.size
        logo_size = qr_width // 4
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)
        qr_img.paste(logo, pos, mask=logo if logo.mode in ("RGBA", "LA") else None)

    buffered = io.BytesIO()
    qr_img.save(buffered, format="PNG")
    buffered.seek(0)

    qr_b64 = base64.b64encode(buffered.getvalue()).decode()
    qr_b64_str = f"data:image/png;base64,{qr_b64}"

    buffered.seek(0)
    upload = cloudinary.uploader.upload(
        buffered,
        folder="employee_qrcodes",
        public_id=employee_id,
        overwrite=True
    )

    return upload.get("secure_url"), qr_b64_str

# ---------------- Template Filter ----------------
@app.template_filter("datetimeformat")
def datetimeformat(value):
    """YYYY-MM-DD → DD/MM/YYYY"""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return value

# =========================================================
# ROUTES
# =========================================================

@app.route("/")
def index():
    return render_template("index.html", employees=employees)

# ---------------- ADD EMPLOYEE ----------------
@app.route("/add", methods=["GET", "POST"])
def add_employee_page():
    message = None
    new_employee_id = None
    json_output = None

    if request.method == "POST":
        employee_id = request.form["employee_id"].strip()
        name = request.form["name"].strip()
        dob_raw = request.form["dob"]  # ✅ YYYY-MM-DD from browser

        try:
            dob = datetime.strptime(dob_raw, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            message = "Invalid date selected."
            return render_template(
                "add_employee_form.html",
                message=message,
                employees=employees
            )

        if employee_id in employees:
            message = f"Employee ID {employee_id} already exists!"
        else:
            employee_data = {
                "ID": employee_id,
                "Name": name,
                "Date of Birth": dob,
                "Gender": request.form["gender"],
                "Emergency Details": {
                    "Blood group": request.form["blood_group"],
                    "Contact Person Name": request.form["contact_person_name"],
                    "Relation": request.form["relation"],
                    "Phone Number": request.form["phone_number"],
                    "Company Phone Number": request.form["company_phone_number"]
                }
            }

            cloud_url, qr_b64 = generate_qr_code(employee_id, name)

            employees[employee_id] = {
                "details": employee_data,
                "qr_url": cloud_url,
                "qr_base64": qr_b64
            }

            message = f"Employee {name} added successfully!"
            new_employee_id = employee_id
            json_output = json.dumps(employee_data, indent=4)

    return render_template(
        "add_employee_form.html",
        message=message,
        new_employee_id=new_employee_id,
        json_output=json_output,
        employees=employees
    )

# ---------------- EDIT EMPLOYEE ----------------
@app.route("/edit/<employee_id>", methods=["GET", "POST"])
def edit_employee(employee_id):
    if employee_id not in employees:
        return "Employee not found", 404

    emp = employees[employee_id]
    message = None

    if request.method == "POST":
        dob_raw = request.form["dob"]

        try:
            dob = datetime.strptime(dob_raw, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            message = "Invalid date selected."
            return render_template(
                "edit_employee.html",
                employee_id=employee_id,
                employee=emp["details"],
                message=message,
                qr_base64=emp["qr_base64"],
                qr_url=emp["qr_url"]
            )

        emp["details"].update({
            "Name": request.form["name"],
            "Date of Birth": dob,
            "Gender": request.form["gender"],
            "Emergency Details": {
                "Blood group": request.form["blood_group"],
                "Contact Person Name": request.form["contact_person_name"],
                "Relation": request.form["relation"],
                "Phone Number": request.form["phone_number"],
                "Company Phone Number": request.form["company_phone_number"]
            }
        })

        cloud_url, qr_b64 = generate_qr_code(employee_id, emp["details"]["Name"])
        emp["qr_url"] = cloud_url
        emp["qr_base64"] = qr_b64

        message = "Employee details updated successfully!"

    return render_template(
        "edit_employee.html",
        employee_id=employee_id,
        employee=emp["details"],
        message=message,
        qr_base64=emp["qr_base64"],
        qr_url=emp["qr_url"]
    )

# ---------------- DELETE ----------------
@app.route("/delete/<employee_id>", methods=["POST"])
def delete_employee(employee_id):
    employees.pop(employee_id, None)
    return redirect(url_for("index"))

# ---------------- EMERGENCY PAGE ----------------
@app.route("/employee/<employee_id>")
def emergency_details_page(employee_id):
    if employee_id not in employees:
        return "Employee not found", 404

    emp = employees[employee_id]
    return render_template(
        "emergency_details.html",
        employee_id=employee_id,
        employee=emp["details"],
        qr_url=emp["qr_url"],
        qr_base64=emp["qr_base64"]
    )

# ---------------- SEARCH ----------------
@app.route("/edit_employee_search", methods=["GET", "POST"])
def edit_employee_search():
    error_message = None

    if request.method == "POST":
        employee_id = request.form.get("employee_id", "").strip()
        if not employee_id:
            error_message = "Please enter Employee ID."
        elif employee_id not in employees:
            error_message = "Employee not found."
        else:
            return redirect(url_for("edit_employee", employee_id=employee_id))

    return render_template("edit_employee_search.html", error_message=error_message)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(debug=True)
