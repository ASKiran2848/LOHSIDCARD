# generate_qrcodes.py
import qrcode
import os
import sys
from PIL import Image
import json # Import json module

# --- Configuration ---
BASE_SERVER_URL = "http://192.168.0.139:5000" # IMPORTANT: Adjust this for your deployment!
                                          # e.g., "http://192.168.1.105:5000" for local IP
QR_CODES_DIR = "employee_qrcodes"
LOGO_PATH = "company_logo.jpg"
LOGO_SIZE_RATIO = 0.2          # <--- Adjust logo size relative to QR code (e.g., 0.2 to 0.3)
WHITE_PADDING_RATIO = 1.2      # <--- How much larger the white background is than the logo (e.g., 1.1 to 1.3)
DATA_FILE = 'data.json' # Define the JSON file for data storage

# Helper function to load data from JSON file
def load_employee_data():
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {DATA_FILE}. Starting with empty data for QR generation.")
            return {}
    else:
        print(f"Data file '{DATA_FILE}' not found or is empty. No employees to generate QR codes for.")
        return {}

def generate_employee_qr_code(employee_id, employee_details, base_url, logo_path=None, logo_ratio=0.2, padding_ratio=1.2):
    unique_url = f"{base_url}/emergency_details/{employee_id}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(unique_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")

            qr_width, qr_height = img.size
            logo_actual_width = int(qr_width * logo_ratio)
            logo_actual_height = int(qr_height * logo_ratio)
            logo = logo.resize((logo_actual_width, logo_actual_height), Image.Resampling.LANCZOS)

            white_bg_width = int(logo_actual_width * padding_ratio)
            white_bg_height = int(logo_actual_height * padding_ratio)

            white_bg = Image.new('RGB', (white_bg_width, white_bg_height), 'white')

            bg_pos_x = (qr_width - white_bg_width) // 2
            bg_pos_y = (qr_height - white_bg_height) // 2
            
            logo_pos_x = (qr_width - logo_actual_width) // 2
            logo_pos_y = (qr_height - logo_actual_height) // 2

            img.paste(white_bg, (bg_pos_x, bg_pos_y))
            img.paste(logo, (logo_pos_x, logo_pos_y), logo) 
            
            print(f"  Pasted logo '{logo_path}' with white background onto QR code.")

        except Exception as e:
            print(f"  Warning: Could not paste logo with white background. Error: {e}")
            print(f"  Please ensure '{logo_path}' is a valid image file and Pillow is installed.")

    filename = os.path.join(QR_CODES_DIR, f"qr_code_{employee_id}.png")
    img.save(filename)
    print(f"Generated QR code for {employee_details['Name']} (ID: {employee_id})")
    print(f"  Saved to: {filename}")
    print(f"  Encoded URL: {unique_url}\n")
    return filename

def main():
    os.makedirs(QR_CODES_DIR, exist_ok=True)
    
    if not os.path.exists(LOGO_PATH):
        print(f"WARNING: Company logo not found at '{LOGO_PATH}'. QR codes will be generated without a logo.")
        print("Please place your logo file (e.g., company_logo.png) in the same directory as generate_qrcodes.py.")
        print("Or update the LOGO_PATH variable in generate_qrcodes.py to the correct path.\n")
    
    employee_data_from_json = load_employee_data()
    if not employee_data_from_json:
        print("No employee data found to generate QR codes. Please add employees first using the web form.")
        return

    print(f"Generating QR codes. Ensure your Flask app will be accessible at: {BASE_SERVER_URL}")
    print("If you plan to scan with a phone, you might need to use your machine's local IP (e.g., http://192.168.0.105:5000/).\n")

    generated_qrcodes = []
    for emp_id, details in employee_data_from_json.items():
        qr_path = generate_employee_qr_code(emp_id, details, BASE_SERVER_URL, LOGO_PATH, LOGO_SIZE_RATIO, WHITE_PADDING_RATIO)
        generated_qrcodes.append(qr_path)

    print(f"All {len(generated_qrcodes)} QR codes saved in the '{QR_CODES_DIR}' directory.")
    print("You can now run the Flask application using: python app.py")

if __name__ == '__main__':
    main()