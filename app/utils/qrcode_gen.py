import os
import qrcode
from io import BytesIO
import base64
from flask import current_app

def generate_qr_base64(data_url: str) -> str:
    """Generate a QR code as a base64 encoded PNG data URI."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(data_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#1e1b4b", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"

def save_qr_code_file(data_url: str, filename: str) -> str:
    """Save QR code image to the server uploads folder and return relative path."""
    qr_folder = current_app.config.get('QR_FOLDER')
    os.makedirs(qr_folder, exist_ok=True)
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(data_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#1e1b4b", back_color="white")
    filepath = os.path.join(qr_folder, f"{filename}.png")
    img.save(filepath)
    return f"uploads/qrcodes/{filename}.png"
