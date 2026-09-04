from datetime import datetime
from app.models import db

class PlatformProfile(db.Model):
    __tablename__ = 'platform_profiles'

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False, index=True)
    platform_name = db.Column(db.String(50), nullable=False, index=True)  # 'leetcode', 'codechef', 'codeforces', 'github', 'hackerrank', 'gfg'
    username = db.Column(db.String(100), nullable=False)
    profile_url = db.Column(db.String(300), nullable=True)
    avatar_url = db.Column(db.String(300), nullable=True)
    
    # Common normalized numeric fields for fast querying
    problems_solved = db.Column(db.Integer, default=0)
    contest_rating = db.Column(db.Float, default=0.0)
    highest_rating = db.Column(db.Float, default=0.0)
    global_rank = db.Column(db.Integer, default=0)
    stars_or_badges = db.Column(db.Integer, default=0)
    
    # Complete raw stats stored as JSON
    raw_data = db.Column(db.JSON, nullable=True, default=dict)
    
    # Status: 'success', 'simulated', 'failed'
    extraction_status = db.Column(db.String(30), default='success')
    error_message = db.Column(db.String(300), nullable=True)
    extracted_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'submission_id': self.submission_id,
            'platform': self.platform_name,
            'username': self.username,
            'profile_url': self.profile_url,
            'avatar_url': self.avatar_url,
            'problems_solved': self.problems_solved,
            'contest_rating': self.contest_rating,
            'highest_rating': self.highest_rating,
            'global_rank': self.global_rank,
            'stars_or_badges': self.stars_or_badges,
            'extraction_status': self.extraction_status,
            'raw_data': self.raw_data or {},
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None
        }
