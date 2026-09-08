import os
import ssl
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

DEFAULT_FROM = "SSVS Verification <noreply@ssvs.edu>"


def _get_config_val(key: str, default=None):
    """Retrieve config parameter from Flask current_app or environment fallback."""
    try:
        from flask import current_app
        if current_app:
            return current_app.config.get(key, default)
    except (ImportError, RuntimeError):
        pass
    return os.environ.get(key, default)


def get_smtp_config() -> Dict[str, Any]:
    """Extract and validate SMTP settings from Flask config / environment."""
    host = _get_config_val('SMTP_HOST', 'smtp.gmail.com') or 'smtp.gmail.com'
    raw_port = _get_config_val('SMTP_PORT', 587)
    try:
        port = int(raw_port)
    except (ValueError, TypeError):
        port = 587

    user = _get_config_val('SMTP_USER', '') or ''
    password = _get_config_val('SMTP_PASSWORD', '') or ''
    use_tls = str(_get_config_val('SMTP_USE_TLS', 'True')).lower() in ('true', '1', 'yes')
    use_ssl = str(_get_config_val('SMTP_USE_SSL', 'False')).lower() in ('true', '1', 'yes')
    from_email = _get_config_val('SMTP_FROM_EMAIL', '') or user or DEFAULT_FROM
    is_testing = str(_get_config_val('TESTING', 'False')).lower() in ('true', '1', 'yes')

    return {
        'host': str(host).strip(),
        'port': port,
        'user': str(user).strip(),
        'password': str(password).strip(),
        'use_tls': use_tls,
        'use_ssl': use_ssl,
        'from_email': str(from_email).strip(),
        'is_testing': is_testing
    }


def send_smtp_email(to_email: str, subject: str, html_content: str, text_content: str = None) -> Tuple[bool, str]:
    """
    Sends an email using standard SMTP authentication (Nodemailer-style transport via smtplib).
    Supports STARTTLS (port 587), SSL (port 465), or local dev/test mock fallback.
    Returns (success: bool, info_message: str).
    """
    if not to_email or '@' not in to_email:
        return False, "Invalid recipient email address."

    target_email = to_email.strip()
    cfg = get_smtp_config()

    # Local development & automated testing mock fallback
    if cfg['is_testing'] or (not cfg['password'] and os.environ.get('FLASK_ENV') != 'production'):
        logger.info(f"[DEV/TEST MOCK SMTP] Dispatched to {target_email} | Subject: {subject}")
        return True, "mock-smtp-dispatched"

    if not cfg['password']:
        err = "SMTP_PASSWORD is not configured in server environment. Please set SMTP credentials."
        logger.error(err)
        return False, err

    # Construct standard MIME multipart email message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = cfg['from_email']
    msg['To'] = target_email

    if text_content:
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))

    if html_content:
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    try:
        if cfg['use_ssl'] or cfg['port'] == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg['host'], cfg['port'], context=context, timeout=15) as server:
                if cfg['user'] and cfg['password']:
                    server.login(cfg['user'], cfg['password'])
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg['host'], cfg['port'], timeout=15) as server:
                if cfg['use_tls']:
                    context = ssl.create_default_context()
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                if cfg['user'] and cfg['password']:
                    server.login(cfg['user'], cfg['password'])
                server.send_message(msg)

        logger.info(f"Email successfully dispatched to {target_email} via SMTP ({cfg['host']}:{cfg['port']}).")
        return True, "smtp-dispatched"

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed for {cfg['user']} on {cfg['host']}: {e}")
        return False, "SMTP authentication failed. Please verify your SMTP user and app password."
    except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError) as e:
        logger.error(f"SMTP connection failed to {cfg['host']}:{cfg['port']}: {e}")
        return False, f"Failed to connect to SMTP mail server ({cfg['host']}:{cfg['port']})."
    except smtplib.SMTPException as e:
        logger.error(f"SMTP transmission error to {target_email}: {e}")
        return False, f"SMTP delivery error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error sending email via SMTP to {target_email}: {e}")
        return False, f"Error sending email: {str(e)}"


def build_otp_html_email(otp_code: str, purpose_label: str, validity_minutes: int = 10) -> str:
    """Builds a responsive, modern HTML email template for OTP delivery."""
    formatted_otp = f"{otp_code[:3]} {otp_code[3:]}" if len(otp_code) == 6 else otp_code
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your SSVS Verification Code</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background-color: #0f172a;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      color: #e2e8f0;
    }}
    .container {{
      max-width: 560px;
      margin: 30px auto;
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
    }}
    .header {{
      background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
      padding: 32px 24px;
      text-align: center;
      color: #ffffff;
    }}
    .header h1 {{
      margin: 0 0 6px 0;
      font-size: 24px;
      font-weight: 800;
      letter-spacing: -0.5px;
    }}
    .header p {{
      margin: 0;
      font-size: 13px;
      opacity: 0.85;
      text-transform: uppercase;
      letter-spacing: 1px;
    }}
    .content {{
      padding: 36px 28px;
      text-align: center;
    }}
    .greeting {{
      font-size: 18px;
      font-weight: 600;
      color: #f8fafc;
      margin-bottom: 12px;
    }}
    .description {{
      font-size: 14px;
      color: #94a3b8;
      line-height: 1.6;
      margin-bottom: 28px;
    }}
    .otp-box {{
      background: #0f172a;
      border: 2px dashed #6366f1;
      border-radius: 12px;
      padding: 20px 16px;
      margin: 0 auto 28px auto;
      display: inline-block;
    }}
    .otp-code {{
      font-family: 'Courier New', Courier, monospace;
      font-size: 38px;
      font-weight: 800;
      color: #38bdf8;
      letter-spacing: 8px;
      display: block;
    }}
    .expiry-badge {{
      display: inline-block;
      margin-top: 8px;
      padding: 4px 12px;
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #f87171;
      font-size: 12px;
      border-radius: 9999px;
      font-weight: 600;
    }}
    .security-notice {{
      background: rgba(51, 65, 85, 0.5);
      border-left: 3px solid #6366f1;
      border-radius: 6px;
      padding: 12px 16px;
      text-align: left;
      font-size: 12px;
      color: #cbd5e1;
      line-height: 1.5;
      margin-bottom: 20px;
    }}
    .footer {{
      background: #0f172a;
      border-top: 1px solid #334155;
      padding: 20px;
      text-align: center;
      font-size: 11px;
      color: #64748b;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Student Score View System</h1>
      <p>Secure Account Verification</p>
    </div>
    <div class="content">
      <div class="greeting">One-Time Verification Code</div>
      <div class="description">
        You requested a verification code for <strong>{purpose_label}</strong> on the SSVS Portal. Use the 6-digit code below to complete your verification:
      </div>
      <div class="otp-box">
        <span class="otp-code">{formatted_otp}</span>
        <div class="expiry-badge">&#x23F1; Valid for {validity_minutes} minutes</div>
      </div>
      <div class="security-notice">
        <strong>Security Notice:</strong> Never share this code with anyone. SSVS administrators and support staff will never ask for your verification code. If you did not initiate this request, please disregard this email.
      </div>
    </div>
    <div class="footer">
      &copy; 2026 Student Score View System (SSVS). Hosted securely on Render.<br>
      Automated message, please do not reply directly to this email.
    </div>
  </div>
</body>
</html>"""


def send_otp_code_email(to_email: str, otp_code: str, purpose: str = "registration", validity_minutes: int = 10) -> Tuple[bool, str]:
    """
    High-level helper to send OTP email via SMTP with appropriate subject and body based on purpose.
    """
    purpose_titles = {
        "registration": ("Faculty Account Registration", "SSVS — Verify Your Faculty Account (OTP Code)"),
        "password_reset": ("Password Reset", "SSVS — Password Reset Verification Code"),
        "login": ("Teacher Login Authentication", "SSVS — Teacher Login Verification Code"),
        "login_verification": ("Account Login Verification", "SSVS — Login Authentication Code"),
        "email_verification": ("Email Verification", "SSVS — Email Verification Code")
    }

    purpose_label, subject = purpose_titles.get(purpose, ("Account Verification", f"SSVS — Verification Code: {otp_code}"))
    html = build_otp_html_email(otp_code, purpose_label, validity_minutes)
    text = (
        f"SSVS Verification Code: {otp_code}\n\n"
        f"This code is requested for {purpose_label} and will expire in {validity_minutes} minutes.\n"
        f"If you did not request this, please ignore this message.\n\n"
        f"— Student Score View System (SSVS)"
    )

    return send_smtp_email(to_email, subject, html, text)
