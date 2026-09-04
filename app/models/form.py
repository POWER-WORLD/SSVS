import uuid
from datetime import datetime
from app.models import db

class Form(db.Model):
    __tablename__ = 'forms'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    title = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text, nullable=True)
    instructions = db.Column(db.Text, nullable=True)
    college_logo = db.Column(db.String(300), nullable=True)
    theme_color = db.Column(db.String(20), default='#4f46e5')
    
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False, index=True)
    
    # Publishing & access control
    is_published = db.Column(db.Boolean, default=False)
    is_closed = db.Column(db.Boolean, default=False)
    deadline = db.Column(db.DateTime, nullable=True)
    max_responses = db.Column(db.Integer, nullable=True)
    allow_edit = db.Column(db.Boolean, default=False)
    one_per_roll = db.Column(db.Boolean, default=True)
    one_per_email = db.Column(db.Boolean, default=True)
    one_per_phone = db.Column(db.Boolean, default=False)
    enable_leaderboard = db.Column(db.Boolean, default=True)
    is_public = db.Column(db.Boolean, default=True)
    qr_code_path = db.Column(db.String(300), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    fields = db.relationship('FormField', backref='form', lazy='dynamic', cascade='all, delete-orphan', order_by='FormField.display_order')
    submissions = db.relationship('Submission', backref='form', lazy='dynamic', cascade='all, delete-orphan')
    formulas = db.relationship('ScoreFormula', backref='form', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def submission_count(self):
        return self.submissions.count()

    @property
    def is_open(self):
        if not self.is_published or self.is_closed:
            return False
        if self.deadline and datetime.utcnow() > self.deadline:
            return False
        if self.max_responses and self.submission_count >= self.max_responses:
            return False
        return True

    def to_dict(self, include_fields=False):
        data = {
            'id': self.id,
            'uuid': self.uuid,
            'slug': self.slug,
            'title': self.title,
            'description': self.description,
            'instructions': self.instructions,
            'theme_color': self.theme_color,
            'is_published': self.is_published,
            'is_closed': self.is_closed,
            'is_open': self.is_open,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'max_responses': self.max_responses,
            'submission_count': self.submission_count,
            'enable_leaderboard': self.enable_leaderboard,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'teacher': {
                'id': self.teacher.id,
                'name': self.teacher.full_name,
                'college': self.teacher.college_name,
                'department': self.teacher.department
            } if self.teacher else None
        }
        if include_fields:
            data['fields'] = [f.to_dict(include_options=True) for f in self.fields.all()]
        return data


class FormField(db.Model):
    __tablename__ = 'form_fields'

    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False, index=True)
    field_key = db.Column(db.String(80), nullable=False)
    label = db.Column(db.String(200), nullable=False)
    field_type = db.Column(db.String(50), nullable=False, default='text')
    placeholder = db.Column(db.String(250), nullable=True)
    help_text = db.Column(db.String(300), nullable=True)
    is_required = db.Column(db.Boolean, default=False)
    default_value = db.Column(db.String(300), nullable=True)
    section_title = db.Column(db.String(150), nullable=True)
    display_order = db.Column(db.Integer, default=0, index=True)
    
    # Platform / scoring integration binding
    # e.g., 'roll_number', 'student_name', 'email', 'phone', 'department', 'cgpa', 'backlogs',
    #       'leetcode_handle', 'codechef_handle', 'codeforces_handle', 'github_handle', 'hackerrank_handle', 'gfg_handle'
    platform_metric_binding = db.Column(db.String(80), nullable=True)
    
    # Stored as JSON strings/dicts
    validation_rules = db.Column(db.JSON, nullable=True, default=dict)
    conditional_rules = db.Column(db.JSON, nullable=True, default=dict)

    # Relationships
    options = db.relationship('FieldOption', backref='field', lazy='dynamic', cascade='all, delete-orphan', order_by='FieldOption.display_order')

    def to_dict(self, include_options=True):
        data = {
            'id': self.id,
            'form_id': self.form_id,
            'field_key': self.field_key,
            'label': self.label,
            'field_type': self.field_type,
            'placeholder': self.placeholder,
            'help_text': self.help_text,
            'is_required': self.is_required,
            'default_value': self.default_value,
            'section_title': self.section_title,
            'display_order': self.display_order,
            'platform_metric_binding': self.platform_metric_binding,
            'validation_rules': self.validation_rules or {},
            'conditional_rules': self.conditional_rules or {}
        }
        if include_options:
            data['options'] = [opt.to_dict() for opt in self.options.all()]
        return data


class FieldOption(db.Model):
    __tablename__ = 'field_options'

    id = db.Column(db.Integer, primary_key=True)
    field_id = db.Column(db.Integer, db.ForeignKey('form_fields.id'), nullable=False, index=True)
    label = db.Column(db.String(200), nullable=False)
    value = db.Column(db.String(200), nullable=False)
    display_order = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'label': self.label,
            'value': self.value,
            'display_order': self.display_order
        }
