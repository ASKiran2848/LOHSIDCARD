import qrcode
from PIL import Image
import os
import json

# --- Configuration ---
BASE_SERVER_URL = "http://YOUR_SERVER_IP:5000"  # Change to your server IP or domain
QR_CODES_DIR = os.path.join("static", "employee_qrcodes")
LOGO_PATH = "static/images/company_logo.jpg"
LOGO_SIZE_RATIO = 0.2
WHITE_PADDING_RATIO = 1.2
DATA_FILE = 'data.json'

# Load employee data
def load_employee_data():
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Error decoding JSON. Starting empty.")
            return {}
    return {}

# Generate QR code
def generate_employee_qr_code(employee_id, employee_details):
    unique_url = f"{BASE_SERVER_URL}/emergency_details/{employee_id}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(unique_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # Add logo if exists
    if LOGO_PATH and os.path.exists(LOGO_PATH):
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            qr_width, qr_height = img.size
            logo_size = int(qr_width * LOGO_SIZE_RATIO)
            logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)

            # White background behind logo
            white_bg_size = int(logo_size * WHITE_PADDING_RATIO)
            white_bg = Image.new('RGB', (white_bg_size, white_bg_size), 'white')
            bg_pos = ((qr_width - white_bg_size) // 2, (qr_height - white_bg_size) // 2)
            img.paste(white_bg, bg_pos)

            logo_pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)
            img.paste(logo, logo_pos, logo)

        except Exception as e:
            print(f"Warning: Could not add logo. Error: {e}")

    os.makedirs(QR_CODES_DIR, exist_ok=True)
    filename = os.path.join(QR_CODES_DIR, f"qr_code_{employee_id}.png")
    img.save(filename)
    print(f"Generated QR for {employee_details['Name']} -> {filename}")
    return filename

# Main
def main():
    employees = load_employee_data()
    if not employees:
        print("No employee data found. Add employees first.")
        return

    for emp_id, details in employees.items():
        generate_employee_qr_code(emp_id, details)

    print(f"Generated QR codes for {len(employees)} employees in '{QR_CODES_DIR}'")

if __name__ == '__main__':
    main()
