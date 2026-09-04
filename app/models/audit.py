from datetime import datetime
from app.models import db

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'description': self.description,
            'created_at': self.created_at.strftime('%b %d, %Y %I:%M %p') if self.created_at else None
        }
