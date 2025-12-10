# app.py
from flask import Flask, render_template, abort, request, redirect, url_for, jsonify
import json
import random
import string
import os # Import os for file path checks

app = Flask(__name__)

# --- Configuration ---
BASE_URL = "http://192.168.0.139:5000" # IMPORTANT: Adjust this for your deployment!
DATA_FILE = 'data.json' # Define the JSON file for data storage

# Global variable to hold employee data (loaded from JSON)
employee_data_db = {}

# Helper function to load data from JSON file
def load_employee_data():
    global employee_data_db
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        try:
            with open(DATA_FILE, 'r') as f:
                employee_data_db = json.load(f)
            print(f"Loaded {len(employee_data_db)} employees from {DATA_FILE}")
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {DATA_FILE}. Starting with empty data.")
            employee_data_db = {}
    else:
        print(f"Data file '{DATA_FILE}' not found or is empty. Starting with empty data.")
        employee_data_db = {}

# Helper function to save data to JSON file
def save_employee_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(employee_data_db, f, indent=4)
    print(f"Saved {len(employee_data_db)} employees to {DATA_FILE}")

# Initialize data on app startup
load_employee_data()

# Removed the generate_unique_employee_id function as it's no longer needed for new employee creation

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/emergency_details/<employee_id>')
def emergency_details_page(employee_id):
    """
    Renders the emergency details page for a specific employee ID.
    """
    employee = employee_data_db.get(employee_id)

    if not employee:
        abort(404, description=f"Employee details for ID '{employee_id}' not found.")

    return render_template('emergency_details.html', employee=employee, employee_id=employee_id)

@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        # Get the employee_id directly from the form input
        new_employee_id = request.form['employee_id'].strip() # Use .strip() to remove leading/trailing whitespace

        # Basic validation: Check if employee_id is provided and if it already exists
        if not new_employee_id:
            return render_template('add_employee_form.html', 
                                   message="Error: Employee ID cannot be empty.", 
                                   message_type="error") # Add a message_type to style errors differently if you wish
        if new_employee_id in employee_data_db:
            return render_template('add_employee_form.html', 
                                   message=f"Error: Employee ID '{new_employee_id}' already exists. Please use a unique ID.", 
                                   message_type="error")

        employee_name = request.form['name']
        dob = request.form['dob']
        gender = request.form['gender']
        blood_group = request.form['blood_group']
        contact_person_name = request.form['contact_person_name']
        relation = request.form['relation']
        phone_number = request.form['phone_number']
        company_phone_number = request.form['company_phone_number']

        new_employee_data = {
            "Name": employee_name,
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

        # Add to the global dictionary using the user-provided ID
        employee_data_db[new_employee_id] = new_employee_data
        # Save the updated dictionary to the JSON file
        save_employee_data()

        json_output = json.dumps({new_employee_id: new_employee_data}, indent=4)
        print(f"NEW EMPLOYEE DATA ADDED & SAVED:\n{json_output}")

        return render_template('add_employee_form.html',
                               message=f"Employee '{employee_name}' added successfully! ID: {new_employee_id}",
                               json_output=json_output,
                               new_employee_id=new_employee_id)

    return render_template('add_employee_form.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)