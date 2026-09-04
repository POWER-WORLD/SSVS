from datetime import datetime
from app.models import db

class ScoreFormula(db.Model):
    __tablename__ = 'score_formulas'

    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False, default="Standard Placement Evaluation")
    description = db.Column(db.String(300), nullable=True)
    normalization_method = db.Column(db.String(50), default='min_max')  # 'min_max', 'percentile', 'z_score', 'weighted_sum'
    max_total_marks = db.Column(db.Float, default=100.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rules = db.relationship('FormulaRule', backref='formula', lazy='dynamic', cascade='all, delete-orphan')
    scores = db.relationship('CalculatedScore', backref='formula', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self, include_rules=True):
        data = {
            'id': self.id,
            'form_id': self.form_id,
            'name': self.name,
            'description': self.description,
            'normalization_method': self.normalization_method,
            'max_total_marks': self.max_total_marks,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_rules:
            data['rules'] = [r.to_dict() for r in self.rules.all()]
        return data


class FormulaRule(db.Model):
    __tablename__ = 'formula_rules'

    id = db.Column(db.Integer, primary_key=True)
    formula_id = db.Column(db.Integer, db.ForeignKey('score_formulas.id'), nullable=False, index=True)
    metric_key = db.Column(db.String(80), nullable=False)  # 'cgpa', 'leetcode_solved', 'leetcode_rating', 'codechef_rating', 'github_contributions', 'backlogs_penalty'
    display_label = db.Column(db.String(150), nullable=False)
    weight_percentage = db.Column(db.Float, default=10.0)
    max_marks = db.Column(db.Float, default=10.0)
    multiplier = db.Column(db.Float, default=1.0)
    penalty_per_unit = db.Column(db.Float, default=0.0)
    bonus_threshold = db.Column(db.Float, default=0.0)
    bonus_marks = db.Column(db.Float, default=0.0)
    category = db.Column(db.String(50), default='coding')  # 'academic', 'coding', 'github', 'penalty'

    def to_dict(self):
        return {
            'id': self.id,
            'metric_key': self.metric_key,
            'display_label': self.display_label,
            'weight_percentage': self.weight_percentage,
            'max_marks': self.max_marks,
            'multiplier': self.multiplier,
            'penalty_per_unit': self.penalty_per_unit,
            'bonus_threshold': self.bonus_threshold,
            'bonus_marks': self.bonus_marks,
            'category': self.category
        }


class CalculatedScore(db.Model):
    __tablename__ = 'calculated_scores'

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False, index=True)
    formula_id = db.Column(db.Integer, db.ForeignKey('score_formulas.id'), nullable=False, index=True)
    
    total_score = db.Column(db.Float, default=0.0, index=True)
    academic_score = db.Column(db.Float, default=0.0)
    coding_score = db.Column(db.Float, default=0.0)
    github_score = db.Column(db.Float, default=0.0)
    penalty_deductions = db.Column(db.Float, default=0.0)
    bonus_awarded = db.Column(db.Float, default=0.0)
    
    rank = db.Column(db.Integer, default=0, index=True)
    percentile = db.Column(db.Float, default=0.0)
    grade = db.Column(db.String(10), default='A')
    
    breakdown_json = db.Column(db.JSON, nullable=True, default=dict)
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'submission_id': self.submission_id,
            'formula_id': self.formula_id,
            'total_score': round(self.total_score, 2),
            'academic_score': round(self.academic_score, 2),
            'coding_score': round(self.coding_score, 2),
            'github_score': round(self.github_score, 2),
            'penalty_deductions': round(self.penalty_deductions, 2),
            'bonus_awarded': round(self.bonus_awarded, 2),
            'rank': self.rank,
            'percentile': round(self.percentile, 1),
            'grade': self.grade,
            'breakdown': self.breakdown_json or {},
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None
        }


class LeaderboardEntry(db.Model):
    __tablename__ = 'leaderboard_cache'

    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('forms.id'), nullable=False, index=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False, index=True)
    rank = db.Column(db.Integer, nullable=False, index=True)
    student_name = db.Column(db.String(150), nullable=False)
    roll_number = db.Column(db.String(80), nullable=False)
    department = db.Column(db.String(100), nullable=True)
    total_score = db.Column(db.Float, nullable=False, index=True)
    percentile = db.Column(db.Float, default=0.0)
    cgpa = db.Column(db.Float, default=0.0)
    coding_score = db.Column(db.Float, default=0.0)
    github_score = db.Column(db.Float, default=0.0)
    badge_count = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    submission = db.relationship('Submission', backref='leaderboard_entries')
