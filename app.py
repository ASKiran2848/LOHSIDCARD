from flask import Flask, render_template, request, redirect, url_for
import json
from PIL import Image
import qrcode
import io
import base64
import os

app = Flask(__name__)

# In-memory storage for employees
employees = {}

# -------------------- QR Code Generation --------------------
def generate_qr_code(data, logo_path="static/images/company_logo.jpg"):
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

        if logo.mode in ('RGBA', 'LA'):
            qr_img.paste(logo, pos, mask=logo)
        else:
            qr_img.paste(logo, pos)

    # Convert to base64
    buffered = io.BytesIO()
    qr_img.save(buffered, format="PNG")
    qr_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{qr_b64}"

# -------------------- ROUTES --------------------

# Home / Employee List
@app.route('/')
def index():
    return render_template("index.html", employees=employees)

# Add Employee Page
@app.route('/add', methods=['GET', 'POST'])
def add_employee_page():
    message = None
    new_employee_id = None
    json_output = None

    if request.method == 'POST':
        employee_id = request.form['employee_id'].strip()
        name = request.form['name']
        dob = request.form['dob']
        gender = request.form['gender']
        blood_group = request.form['blood_group']
        contact_person_name = request.form['contact_person_name']
        relation = request.form['relation']
        phone_number = request.form['phone_number']
        company_phone_number = request.form['company_phone_number']

        if employee_id in employees:
            message = f"Employee ID {employee_id} already exists!"
        else:
            employee_data = {
                "ID": employee_id,
                "Name": name,
                "Date of Birth": dob,
                "Gender": gender,
                "Emergency Details": {
                    "Blood group": blood_group,
                    "Contact Person Name": contact_person_name,
                    "Relation": relation,
                    "Phone Number": phone_number,
                    "Company Phone Number": company_phone_number
                }
            }

            # Generate URL for QR code
            full_url = request.host_url.rstrip('/') + url_for('emergency_details_page', employee_id=employee_id)
            qr_url = generate_qr_code(full_url)

            employees[employee_id] = {
                "details": employee_data,
                "qr_url": qr_url
            }

            message = f"Employee {name} added successfully!"
            new_employee_id = employee_id
            json_output = json.dumps(employee_data, indent=4)

    return render_template(
        "add_employee_form.html",
        message=message,
        new_employee_id=new_employee_id,
        json_output=json_output
    )

# Edit Employee Search
@app.route('/edit_employee_search', methods=['GET', 'POST'])
def edit_employee_search():
    message = None
    if request.method == 'POST':
        employee_id = request.form.get('employee_id', '').strip()
        if not employee_id:
            message = "Please enter a valid Employee ID."
        elif employee_id not in employees:
            message = f"Employee ID {employee_id} not found."
        else:
            return redirect(url_for('emergency_details_page', employee_id=employee_id))
    return render_template("edit_employee_search.html", message=message)

# Emergency Details Page
@app.route('/employee/<employee_id>')
def emergency_details_page(employee_id):
    if employee_id not in employees:
        return f"Employee ID {employee_id} not found.", 404

    emp = employees[employee_id]
    return render_template(
        "emergency_details.html",
        employee_id=employee_id,
        employee=emp["details"],
        qr_url=emp["qr_url"]
    )

# -------------------- RUN --------------------
if __name__ == "__main__":
    app.run(debug=True)
