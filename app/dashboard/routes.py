from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.form import Form
from app.models.submission import Submission
from app.models.scoring import LeaderboardEntry
from app.models.audit import ActivityLog

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    featured_form = Form.query.filter_by(is_published=True, is_public=True).first()
    if current_user.is_authenticated:
        return render_template('landing.html', user=current_user, featured_form=featured_form)
    return render_template('landing.html', featured_form=featured_form)

@dashboard_bp.route('/dashboard')
@login_required
def overview():
    forms = current_user.forms.order_by(Form.created_at.desc()).all()
    form_ids = [f.id for f in forms]
    
    total_forms = len(forms)
    active_forms = sum(1 for f in forms if f.is_open)
    total_submissions = Submission.query.filter(Submission.form_id.in_(form_ids)).count() if form_ids else 0
    
    # Calculate global top and average scores
    entries = LeaderboardEntry.query.filter(LeaderboardEntry.form_id.in_(form_ids)).all() if form_ids else []
    scores = [e.total_score for e in entries]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    highest_score = round(max(scores), 1) if scores else 0.0
    
    # Recent submissions
    recent_submissions = Submission.query.filter(Submission.form_id.in_(form_ids))\
        .order_by(Submission.submitted_at.desc()).limit(8).all() if form_ids else []
        
    recent_logs = current_user.activity_logs.order_by(ActivityLog.created_at.desc()).limit(6).all()

    return render_template(
        'dashboard/overview.html',
        forms=forms,
        total_forms=total_forms,
        active_forms=active_forms,
        total_submissions=total_submissions,
        avg_score=avg_score,
        highest_score=highest_score,
        recent_submissions=recent_submissions,
        recent_logs=recent_logs
    )
