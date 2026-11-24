"""
========================================================================================
Student Score View System (SSVS) - Google Apps Script (GAS) Email Gateway Service
========================================================================================
Description : Enterprise email dispatching via Google Apps Script WebApp.
              Replaces legacy direct SMTP/Nodemailer transports to eliminate cloud
              firewall port blocks (ports 25, 465, 587) on container platforms such
              as Render, AWS, and Docker.
Security    : End-to-end tokenized authorization (GAS_SECRET_TOKEN) over TLS (Port 443).
Author      : Senior Software Architect & Platform Engineer
========================================================================================
"""

import os
import logging
from typing import Tuple, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)


def _get_config_val(key: str, default=None):
    """Retrieve configuration parameter from Flask current_app or environment fallback."""
    try:
        from flask import current_app
        if current_app:
            return current_app.config.get(key, default)
    except (ImportError, RuntimeError):
        pass
    return os.environ.get(key, default)


def get_gas_config() -> Dict[str, Any]:
    """
    Extract and validate Google Apps Script email settings from Flask config / environment.
    Returns:
        Dict containing url, token, timeout, and is_testing flag.
    """
    url = _get_config_val('GAS_EMAIL_URL', '') or ''
    token = _get_config_val('GAS_SECRET_TOKEN', '') or ''
    raw_timeout = _get_config_val('GAS_REQUEST_TIMEOUT', 15)
    try:
        timeout = int(raw_timeout)
    except (ValueError, TypeError):
        timeout = 15

    is_testing = str(_get_config_val('TESTING', 'False')).lower() in ('true', '1', 'yes')

    return {
        'url': str(url).strip(),
        'token': str(token).strip(),
        'timeout': timeout,
        'is_testing': is_testing
    }


def send_gas_email(to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> Tuple[bool, str]:
    """
    Dispatches an email through Google Apps Script Web App using an authorized HTTP POST request.
    Payload schema matching Google Apps Script doPost(e):
        {
            "token": "<SECRET_TOKEN>",
            "to": "<recipient@domain.com>",
            "subject": "<Email Subject>",
            "html": "<p>HTML Body Content</p>"
        }
    Returns:
        (success: bool, status_message: str)
    """
    if not to_email or '@' not in to_email:
        return False, "Invalid recipient email address."

    target_email = to_email.strip()
    cfg = get_gas_config()

    # Local development & automated testing mock fallback
    if cfg['is_testing'] or (not cfg['url'] and os.environ.get('FLASK_ENV') != 'production' and not os.environ.get('RENDER')):
        logger.info(f"[DEV/TEST MOCK GAS EMAIL] Dispatched to {target_email} | Subject: {subject}")
        return True, "mock-gas-dispatched"

    if not cfg['url'] or not cfg['token']:
        err = "Google Apps Script email service is not configured (missing GAS_EMAIL_URL or GAS_SECRET_TOKEN in server environment)."
        logger.error(err)
        return False, err

    payload = {
        'token': cfg['token'],
        'to': target_email,
        'subject': subject,
        'html': html_content
    }

    try:
        logger.info(f"Dispatching email to {target_email} via Google Apps Script WebApp gateway...")
        response = requests.post(
            cfg['url'],
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'SSVS-Portal-Email-Gateway/2.0'
            },
            timeout=cfg['timeout'],
            allow_redirects=True
        )

        # Attempt JSON decoding of Google Apps Script ContentService output
        try:
            data = response.json()
        except Exception:
            text_resp = response.text.strip()
            if "Email sent" in text_resp:
                logger.info(f"Email successfully dispatched to {target_email} via Google Apps Script (text response).")
                return True, "Email sent"
            logger.error(f"Unexpected non-JSON response from Google Apps Script: {text_resp}")
            return False, f"Unexpected response from email service: {text_resp[:200]}"

        if isinstance(data, dict):
            if data.get('success'):
                msg = data.get('message', 'Email sent')
                logger.info(f"Email successfully dispatched to {target_email} via Google Apps Script: {msg}")
                return True, msg
            else:
                err = data.get('error', 'Failed to dispatch email')
                logger.error(f"Google Apps Script rejected email to {target_email}: {err}")
                return False, f"Email delivery failed: {err}"

        return False, f"Invalid response format received from Google Apps Script: {data}"

    except requests.Timeout:
        err = f"Google Apps Script email service timed out after {cfg['timeout']}s."
        logger.error(err)
        return False, err
    except requests.ConnectionError as e:
        err = f"Network connection error contacting Google Apps Script: {str(e)}"
        logger.error(err)
        return False, err
    except requests.RequestException as e:
        err = f"HTTP error during Google Apps Script email dispatch: {str(e)}"
        logger.error(err)
        return False, err
    except Exception as e:
        err = f"Unexpected error dispatching email via Google Apps Script: {str(e)}"
        logger.error(err)
        return False, err


# Clean backward-compatible aliases
send_email = send_gas_email
send_smtp_email = send_gas_email


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
      &copy; 2026 Student Score View System (SSVS). Powered by Google Apps Script.<br>
      Automated message, please do not reply directly to this email.
    </div>
  </div>
</body>
</html>"""


def send_otp_code_email(to_email: str, otp_code: str, purpose: str = "registration", validity_minutes: int = 10) -> Tuple[bool, str]:
    """
    Dispatches OTP verification code email using Google Apps Script Web App.
    Logs OTP to server console as an emergency diagnostic backup.
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

    # Always log OTP in server logs as an emergency backup for cloud diagnostics
    logger.info("=" * 65)
    logger.info(f"[SSVS OTP CODE] Recipient: {to_email} | Purpose: {purpose} | Code: {otp_code}")
    logger.info("=" * 65)

    # Dispatch via Google Apps Script gateway
    success, msg = send_gas_email(to_email, subject, html, text)
    return success, msg
