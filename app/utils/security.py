import re
import secrets
import string
import unicodedata
from werkzeug.utils import secure_filename

def slugify(value: str) -> str:
    """Converts string into clean URL-friendly slug with unique random suffix."""
    value = unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    slug_base = re.sub(r'[-\s]+', '-', value)[:50]
    random_suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    return f"{slug_base}-{random_suffix}" if slug_base else f"form-{random_suffix}"

def is_allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Checks if uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
