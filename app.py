from flask import Flask, render_template, abort, request
import json
import os
from generate_qrcodes import generate_employee_qr_code, load_employee_data

app = Flask(__name__)

# --- Configuration ---
BASE_URL = "http://YOUR_SERVER_IP:5000"  # Change to your server IP or domain
DATA_FILE = 'data.json'

# AWS S3 Configuration (use environment variables for security)
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Global variable to hold employee data
employee_data_db = {}

# --- Load employee data ---
def load_data():
    global employee_data_db
    employee_data_db = load_employee_data()

# --- Save employee data ---
def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(employee_data_db, f, indent=4)
    print(f"Saved {len(employee_data_db)} employees to {DATA_FILE}")

# --- Initialize ---
load_data()

# --- Routes ---
@app.route('/')
def index():
    employees = {}
    for emp_id, details in employee_data_db.items():
        qr_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/employee_qrcodes/qr_code_{emp_id}.png"
        employees[emp_id] = {"details": details, "qr_url": qr_url}
    return render_template('index.html', employees=employees)

@app.route('/emergency_details/<employee_id>')
def emergency_details_page(employee_id):
    employee = employee_data_db.get(employee_id)
    if not employee:
        abort(404, description=f"Employee ID '{employee_id}' not found.")
    qr_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/employee_qrcodes/qr_code_{employee_id}.png"
    return render_template('emergency_details.html', employee=employee, employee_id=employee_id, qr_url=qr_url)

@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        new_employee_id = request.form['employee_id'].strip()
        if not new_employee_id:
            return render_template('add_employee_form.html', message="Employee ID cannot be empty.", message_type="error")
        if new_employee_id in employee_data_db:
            return render_template('add_employee_form.html', message=f"Employee ID '{new_employee_id}' already exists.", message_type="error")

        new_employee_data = {
            "Name": request.form['name'],
            "Date of Birth": request.form['dob'],
            "Gender": request.form['gender'],
            "Emergency Details": {
                "Blood group": request.form['blood_group'],
                "Contact Person Name": request.form['contact_person_name'],
                "Relation": request.form['relation'],
                "Phone Number": request.form['phone_number'],
                "Company Phone Number": request.form['company_phone_number']
            }
        }

        employee_data_db[new_employee_id] = new_employee_data
        save_data()

        # Generate QR code and upload to S3
        generate_employee_qr_code(new_employee_id, new_employee_data)

        return render_template('add_employee_form.html',
                               message=f"Employee '{new_employee_data['Name']}' added successfully! ID: {new_employee_id}",
                               new_employee_id=new_employee_id)

    return render_template('add_employee_form.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
