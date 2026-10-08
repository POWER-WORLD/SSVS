from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import db
from app.models.form import Form
from app.models.submission import Submission
from app.models.scoring import LeaderboardEntry
from app.models.audit import ActivityLog

import time

dashboard_bp = Blueprint('dashboard', __name__)

_featured_form_cache = {'timestamp': 0, 'form': None}

@dashboard_bp.route('/')
def index():
    now = time.time()
    # Cache featured form for 30 seconds to provide lightning-fast sub-2ms landing page response
    if now - _featured_form_cache['timestamp'] > 30:
        try:
            featured = Form.query.options(db.joinedload(Form.teacher)).filter_by(is_published=True, is_public=True).first()
            if featured:
                featured._submission_count_cache = Submission.query.filter_by(form_id=featured.id).count()
            _featured_form_cache['form'] = featured
            _featured_form_cache['timestamp'] = now
        except Exception:
            featured = _featured_form_cache['form']
    else:
        featured = _featured_form_cache['form']

    if current_user.is_authenticated:
        return render_template('landing.html', user=current_user, featured_form=featured)
    return render_template('landing.html', featured_form=featured)

@dashboard_bp.route('/dashboard')
@login_required
def overview():
    forms = current_user.forms.order_by(Form.created_at.desc()).all()
    form_ids = [f.id for f in forms]
    total_forms = len(forms)

    if form_ids:
        # 1. Batch query submission counts for all forms in a single SQL query
        sub_counts = dict(
            db.session.query(Submission.form_id, db.func.count(Submission.id))
            .filter(Submission.form_id.in_(form_ids))
            .group_by(Submission.form_id).all()
        )
        for f in forms:
            f._submission_count_cache = sub_counts.get(f.id, 0)

        total_submissions = sum(sub_counts.values())
        active_forms = sum(1 for f in forms if f.is_open)

        # 2. Fast SQL aggregation for cohort mean and top score
        stats = db.session.query(
            db.func.avg(LeaderboardEntry.total_score),
            db.func.max(LeaderboardEntry.total_score)
        ).filter(LeaderboardEntry.form_id.in_(form_ids)).first()
        
        avg_score = round(float(stats[0] or 0.0), 1) if stats else 0.0
        highest_score = round(float(stats[1] or 0.0), 1) if stats else 0.0

        # 3. Preload latest score and profiles for recent submissions
        recent_submissions = Submission.query.filter(Submission.form_id.in_(form_ids))\
            .order_by(Submission.submitted_at.desc()).limit(8).all()
        Submission.preload_for_list(recent_submissions)
    else:
        active_forms = 0
        total_submissions = 0
        avg_score = 0.0
        highest_score = 0.0
        recent_submissions = []

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
