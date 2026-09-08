import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from app.models import db

def utc_now() -> datetime:
    """Return timezone-naive UTC datetime for consistent database storage."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EmailOTP(db.Model):
    __tablename__ = 'email_otps'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    otp_hash = db.Column(db.String(128), nullable=False)
    purpose = db.Column(db.String(50), nullable=False, default='registration', index=True)
    attempts = db.Column(db.Integer, default=0)
    max_attempts = db.Column(db.Integer, default=5)
    is_used = db.Column(db.Boolean, default=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    @staticmethod
    def hash_code(code: str) -> str:
        """Compute cryptographic SHA-256 hash of OTP code."""
        return hashlib.sha256(str(code).strip().encode('utf-8')).hexdigest()

    @staticmethod
    def generate_random_code() -> str:
        """Generate a cryptographically secure 6-digit numeric OTP."""
        return f"{secrets.SystemRandom().randint(100000, 999999)}"

    @classmethod
    def can_resend(cls, email: str, purpose: str, cooldown_seconds: int = 60) -> Tuple[bool, int]:
        """
        Rate limiting check: determines if another OTP can be requested.
        Returns (can_resend: bool, remaining_cooldown_seconds: int).
        """
        normalized_email = email.lower().strip()
        latest = cls.query.filter_by(email=normalized_email, purpose=purpose)\
                          .order_by(cls.created_at.desc()).first()
        if not latest:
            return True, 0

        elapsed = (utc_now() - latest.created_at).total_seconds()
        if elapsed < cooldown_seconds:
            return False, int(cooldown_seconds - elapsed)
        return True, 0

    @classmethod
    def create_otp(cls, email: str, purpose: str = 'registration', validity_minutes: int = 10) -> Tuple['EmailOTP', str]:
        """
        Invalidates any previous unused OTPs for this email and purpose,
        creates a new active 6-digit OTP, saves the hash, and returns (record, raw_code).
        """
        normalized_email = email.lower().strip()
        
        # Invalidate existing active tokens
        active_tokens = cls.query.filter_by(email=normalized_email, purpose=purpose, is_used=False).all()
        for tok in active_tokens:
            tok.is_used = True

        raw_code = cls.generate_random_code()
        hashed = cls.hash_code(raw_code)
        expires = utc_now() + timedelta(minutes=validity_minutes)

        otp_record = cls(
            email=normalized_email,
            otp_hash=hashed,
            purpose=purpose,
            attempts=0,
            max_attempts=5,
            is_used=False,
            expires_at=expires,
            created_at=utc_now()
        )
        db.session.add(otp_record)
        db.session.commit()

        return otp_record, raw_code

    @classmethod
    def verify_otp(cls, email: str, purpose: str, candidate_code: str) -> Tuple[bool, str]:
        """
        Verifies a user-supplied OTP code against the latest valid token.
        Returns (success: bool, status_message: str).
        """
        normalized_email = email.lower().strip()
        cleaned_code = str(candidate_code).strip().replace(" ", "").replace("-", "")

        # Find latest unexpired, unused token
        otp_record = cls.query.filter(
            cls.email == normalized_email,
            cls.purpose == purpose,
            cls.is_used == False,
            cls.expires_at > utc_now()
        ).order_by(cls.created_at.desc()).first()

        if not otp_record:
            return False, "Verification code has expired or was not found. Please request a new code."

        if otp_record.attempts >= otp_record.max_attempts:
            otp_record.is_used = True
            db.session.commit()
            return False, "Too many failed attempts. For your security, this code has been revoked. Please request a new code."

        hashed_candidate = cls.hash_code(cleaned_code)
        if secrets.compare_digest(otp_record.otp_hash, hashed_candidate):
            otp_record.is_used = True
            db.session.commit()
            return True, "Code successfully verified."
        else:
            otp_record.attempts += 1
            db.session.commit()
            remaining = max(0, otp_record.max_attempts - otp_record.attempts)
            if remaining == 0:
                otp_record.is_used = True
                db.session.commit()
                return False, "Incorrect code. Maximum attempts exceeded. Please request a new code."
            return False, f"Incorrect verification code. {remaining} attempt{'s' if remaining != 1 else ''} remaining."

    def __repr__(self):
        return f"<EmailOTP {self.email} purpose={self.purpose} used={self.is_used}>"
