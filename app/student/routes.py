import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from werkzeug.utils import secure_filename
from app.models import db
from app.models.form import Form, FormField
from app.models.submission import Submission, SubmissionValue
from app.models.scoring import LeaderboardEntry, CalculatedScore
from app.utils.background import queue_submission_processing
from app.utils.security import is_allowed_file
from app.utils.qrcode_gen import generate_qr_base64

student_bp = Blueprint('student', __name__)

@student_bp.route('/f/<slug>')
def view_form(slug):
    form = Form.query.filter_by(slug=slug).first_or_404()
    if not form.is_published:
        return render_template('student/form_closed.html', form=form, reason="This assessment form is currently in draft mode and has not been published yet.")
    if form.is_closed:
        return render_template('student/form_closed.html', form=form, reason="This assessment form has been closed by the instructor.")
    if form.deadline and datetime.utcnow() > form.deadline:
        return render_template('student/form_closed.html', form=form, reason=f"The deadline for this assessment passed on {form.deadline.strftime('%b %d, %Y %I:%M %p')}.")
    if form.max_responses and form.submission_count >= form.max_responses:
        return render_template('student/form_closed.html', form=form, reason="This form has reached its maximum response capacity.")

    fields = form.fields.order_by(FormField.display_order.asc()).all()
    
    # Group fields by section title
    sections = {}
    for f in fields:
        sec = f.section_title or 'General Details'
        if sec not in sections:
            sections[sec] = []
        sections[sec].append(f)

    return render_template('student/form_view.html', form=form, fields=fields, sections=sections)

@student_bp.route('/f/<slug>/submit', methods=['POST'])
def submit_form(slug):
    form = Form.query.filter_by(slug=slug).first_or_404()
    if not form.is_open:
        flash('This form is currently not accepting submissions.', 'danger')
        return redirect(url_for('student.view_form', slug=slug))

    fields = form.fields.order_by(FormField.display_order.asc()).all()
    
    extracted_data = {}
    for f in fields:
        if f.field_type == 'file':
            file = request.files.get(f.field_key)
            if file and file.filename and is_allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
                filename = f"{uuid.uuid4().hex[:12]}_{secure_filename(file.filename)}"
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                extracted_data[f.field_key] = f"uploads/{filename}"
            elif f.is_required and not extracted_data.get(f.field_key):
                flash(f'Field "{f.label}" is required.', 'danger')
                return redirect(url_for('student.view_form', slug=slug))
        else:
            val = request.form.get(f.field_key, '').strip()
            if f.is_required and not val:
                flash(f'Field "{f.label}" is required.', 'danger')
                return redirect(url_for('student.view_form', slug=slug))
            extracted_data[f.field_key] = val

    # Extract standard candidate bindings
    student_name = extracted_data.get('student_name') or request.form.get('student_name', 'Student Candidate')
    roll_number = extracted_data.get('roll_number') or request.form.get('roll_number', 'N/A')
    email = extracted_data.get('email') or request.form.get('email', '')
    phone = extracted_data.get('phone') or request.form.get('phone', '')
    department = extracted_data.get('department') or request.form.get('department', 'Computer Science')
    semester = extracted_data.get('semester') or request.form.get('semester', '6')
    batch = extracted_data.get('batch') or request.form.get('batch', '2026')
    
    try:
        cgpa = float(extracted_data.get('cgpa', 0.0))
    except (ValueError, TypeError):
        cgpa = 0.0
        
    try:
        backlogs = int(extracted_data.get('backlogs', 0))
    except (ValueError, TypeError):
        backlogs = 0

    # Duplicate checks
    if form.one_per_roll and roll_number:
        existing = Submission.query.filter_by(form_id=form.id, roll_number=roll_number).first()
        if existing:
            flash(f'A submission with Roll Number "{roll_number}" has already been recorded.', 'warning')
            return redirect(url_for('student.submission_status', uuid=existing.uuid))

    if form.one_per_email and email:
        existing = Submission.query.filter_by(form_id=form.id, email=email).first()
        if existing:
            flash(f'A submission with Email "{email}" has already been recorded.', 'warning')
            return redirect(url_for('student.submission_status', uuid=existing.uuid))

    # Create submission
    submission = Submission(
        form_id=form.id,
        student_name=student_name,
        roll_number=roll_number,
        email=email,
        phone=phone,
        department=department,
        semester=semester,
        batch=batch,
        cgpa=cgpa,
        backlogs=backlogs,
        status='pending',
        ip_address=request.remote_addr
    )
    db.session.add(submission)
    db.session.flush()

    # Save values
    for f in fields:
        val = extracted_data.get(f.field_key)
        if val:
            sub_val = SubmissionValue(
                submission_id=submission.id,
                field_id=f.id,
                value_text=str(val) if f.field_type not in ('file', 'image') else None,
                file_path=str(val) if f.field_type in ('file', 'image') else None
            )
            db.session.add(sub_val)

    db.session.commit()

    # Trigger background worker for scraping and scoring
    queue_submission_processing(submission.id)

    return redirect(url_for('student.submission_status', uuid=submission.uuid))

@student_bp.route('/submission/<uuid>/status')
def submission_status(uuid):
    submission = Submission.query.filter_by(uuid=uuid).first_or_404()
    form = submission.form
    score = submission.latest_score
    profiles = submission.platform_profiles.all()
    
    return render_template(
        'student/status.html',
        submission=submission,
        form=form,
        score=score,
        profiles=profiles
    )

@student_bp.route('/submission/<uuid>/scorecard')
def view_scorecard(uuid):
    submission = Submission.query.filter_by(uuid=uuid).first_or_404()
    form = submission.form
    score = submission.latest_score
    profiles = submission.platform_profiles.all()
    
    # Total candidates count for cohort context
    total_candidates = form.submissions.count()
    
    # Verification URL & QR code
    verify_url = url_for('student.view_scorecard', uuid=submission.uuid, _external=True)
    qr_code_b64 = generate_qr_base64(verify_url)
    
    # Formula & rules breakdown
    formula = form.formulas.filter_by(is_active=True).first()
    breakdown = (score.breakdown_json or {}) if score else {}
    
    # Platform profiles map for easy lookup
    profiles_dict = {p.platform_name.lower(): p for p in profiles}
    
    return render_template(
        'student/scorecard.html',
        submission=submission,
        form=form,
        score=score,
        profiles=profiles,
        profiles_dict=profiles_dict,
        total_candidates=total_candidates,
        qr_code_b64=qr_code_b64,
        formula=formula,
        breakdown=breakdown,
        verify_url=verify_url,
        auto_print=request.args.get('print') == '1'
    )

@student_bp.route('/leaderboard')
def public_leaderboard_search():
    q = request.args.get('q', '').strip()
    college = request.args.get('college', '').strip()
    
    query = Form.query.filter_by(is_published=True, enable_leaderboard=True)
    if q:
        query = query.filter(
            db.or_(
                Form.title.ilike(f'%{q}%'),
                Form.description.ilike(f'%{q}%')
            )
        )
    if college:
        query = query.join(Form.teacher).filter(Form.teacher.has(college_name=college))
        
    forms = query.order_by(Form.created_at.desc()).all()
    
    colleges = [c[0] for c in db.session.query(Form.teacher).join(Form).with_entities(Form.teacher.property.mapper.class_.college_name).distinct().all()] if forms else []
    
    return render_template('leaderboard/public_search.html', forms=forms, query=q, colleges=colleges)

@student_bp.route('/leaderboard/<slug>')
def view_leaderboard(slug):
    form = Form.query.filter_by(slug=slug).first_or_404()
    if not form.enable_leaderboard:
        flash('Leaderboard is disabled for this assessment.', 'warning')
        return redirect(url_for('student.public_leaderboard_search'))

    dept_filter = request.args.get('dept', '').strip()
    search_q = request.args.get('q', '').strip()
    
    query = LeaderboardEntry.query.filter_by(form_id=form.id)
    if dept_filter:
        query = query.filter(LeaderboardEntry.department == dept_filter)
    if search_q:
        query = query.filter(
            db.or_(
                LeaderboardEntry.student_name.ilike(f'%{search_q}%'),
                LeaderboardEntry.roll_number.ilike(f'%{search_q}%')
            )
        )

    entries = query.order_by(LeaderboardEntry.rank.asc()).all()
    
    # Top 3 podium
    top3 = entries[:3]
    podium = {
        'first': top3[0] if len(top3) > 0 else None,
        'second': top3[1] if len(top3) > 1 else None,
        'third': top3[2] if len(top3) > 2 else None
    }
    
    departments = [d[0] for d in db.session.query(LeaderboardEntry.department).filter_by(form_id=form.id).distinct().all() if d[0]]

    return render_template(
        'leaderboard/view.html',
        form=form,
        entries=entries,
        podium=podium,
        departments=departments,
        current_dept=dept_filter,
        search_q=search_q
    )
