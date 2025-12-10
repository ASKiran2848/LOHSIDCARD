import qrcode
from PIL import Image
import io
import json
import os
import boto3

# --- Configuration ---
BASE_SERVER_URL = "http://YOUR_SERVER_IP:5000"  # Change to your server IP or domain
LOGO_PATH = "static/images/company_logo.jpg"
LOGO_SIZE_RATIO = 0.2
WHITE_PADDING_RATIO = 1.2
DATA_FILE = 'data.json'

# S3 Configuration
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
s3_client = boto3.client('s3', region_name=AWS_REGION)

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

# Upload image to S3
def upload_to_s3(img, filename):
    in_mem_file = io.BytesIO()
    img.save(in_mem_file, format="PNG")
    in_mem_file.seek(0)
    s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=filename, Body=in_mem_file, ContentType='image/png')
    # Return public URL
    return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{filename}"

# Generate QR code and upload to S3
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

            white_bg_size = int(logo_size * WHITE_PADDING_RATIO)
            white_bg = Image.new('RGB', (white_bg_size, white_bg_size), 'white')
            bg_pos = ((qr_width - white_bg_size) // 2, (qr_height - white_bg_size) // 2)
            img.paste(white_bg, bg_pos)

            logo_pos = ((qr_width - logo_size) // 2, (qr_height - logo_size) // 2)
            img.paste(logo, logo_pos, logo)
        except Exception as e:
            print(f"Warning: Could not add logo. Error: {e}")

    filename = f"employee_qrcodes/qr_code_{employee_id}.png"
    url = upload_to_s3(img, filename)
    print(f"Generated QR for {employee_details['Name']} -> {url}")
    return url
