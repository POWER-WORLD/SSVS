import uuid
from datetime import datetime
from app.models import db

class Submission(db.Model):
    __tablename__ = 'submissions'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False, index=True)
    
    # Normalized core student identification fields
    student_name = db.Column(db.String(150), nullable=False, index=True)
    roll_number = db.Column(db.String(80), nullable=False, index=True)
    email = db.Column(db.String(150), nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=True)
    department = db.Column(db.String(100), nullable=True, default='Computer Science')
    semester = db.Column(db.String(20), nullable=True, default='6')
    batch = db.Column(db.String(20), nullable=True, default='2026')
    cgpa = db.Column(db.Float, nullable=True, default=0.0)
    backlogs = db.Column(db.Integer, nullable=True, default=0)
    
    # Execution status: 'pending', 'extracting', 'scored', 'completed', 'failed'
    status = db.Column(db.String(30), default='pending', index=True)
    error_message = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Teacher Moderation & Verification
    verification_status = db.Column(db.String(30), default='verified', index=True)  # 'verified', 'pending', 'shortlisted', 'flagged'
    teacher_remarks = db.Column(db.Text, nullable=True)
    manual_score_adjustment = db.Column(db.Float, default=0.0)
    last_modified_by = db.Column(db.String(150), nullable=True)

    # Relationships
    values = db.relationship('SubmissionValue', backref='submission', lazy='dynamic', cascade='all, delete-orphan')
    platform_profiles = db.relationship('PlatformProfile', backref='submission', lazy='dynamic', cascade='all, delete-orphan')
    calculated_scores = db.relationship('CalculatedScore', backref='submission', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def latest_score(self):
        return self.calculated_scores.order_by(db.desc('id')).first()

    def get_value(self, field_key):
        for val in self.values.all():
            if val.field and val.field.field_key == field_key:
                return val.value_text
        return None

    def to_dict(self, include_values=False, include_scores=True):
        data = {
            'id': self.id,
            'uuid': self.uuid,
            'form_id': self.form_id,
            'student_name': self.student_name,
            'roll_number': self.roll_number,
            'email': self.email,
            'phone': self.phone,
            'department': self.department,
            'semester': self.semester,
            'batch': self.batch,
            'cgpa': self.cgpa,
            'backlogs': self.backlogs,
            'status': self.status,
            'verification_status': self.verification_status,
            'teacher_remarks': self.teacher_remarks,
            'manual_score_adjustment': self.manual_score_adjustment,
            'error_message': self.error_message,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None
        }
        if include_scores and self.latest_score:
            data['score'] = self.latest_score.to_dict()
        if include_values:
            data['values'] = [v.to_dict() for v in self.values.all()]
            data['profiles'] = [p.to_dict() for p in self.platform_profiles.all()]
        return data


class SubmissionValue(db.Model):
    __tablename__ = 'submission_values'

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False, index=True)
    field_id = db.Column(db.Integer, db.ForeignKey('form_fields.id'), nullable=False, index=True)
    
    value_text = db.Column(db.Text, nullable=True)
    value_json = db.Column(db.JSON, nullable=True)
    file_path = db.Column(db.String(300), nullable=True)

    # Relationships
    field = db.relationship('FormField', backref='submission_values')

    def to_dict(self):
        return {
            'id': self.id,
            'field_id': self.field_id,
            'field_key': self.field.field_key if self.field else None,
            'label': self.field.label if self.field else None,
            'value': self.value_text or self.value_json or self.file_path,
            'file_path': self.file_path
        }
