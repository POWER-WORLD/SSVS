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
        sec = f.section_title or "General Information"
        if sec not in sections:
            sections[sec] = []
        sections[sec].append(f)

    return render_template('student/form_view.html', form=form, sections=sections, fields=fields)

@student_bp.route('/f/<slug>/submit', methods=['POST'])
def submit_form(slug):
    form = Form.query.filter_by(slug=slug).first_or_404()
    if not form.is_open:
        flash('This form is no longer accepting responses.', 'danger')
        return redirect(url_for('student.view_form', slug=slug))

    fields = form.fields.all()
    field_map = {f.field_key: f for f in fields}
    
    # Extract values and check required
    extracted_data = {}
    missing_required = []
    
    for f in fields:
        val = None
        if f.field_type == 'file' or f.field_type == 'image':
            file = request.files.get(f.field_key)
            if file and file.filename:
                if is_allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
                    sec_name = secure_filename(f"{form.id}_{f.field_key}_{file.filename}")
                    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], sec_name)
                    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
                    file.save(upload_path)
                    val = f"uploads/{sec_name}"
        elif f.field_type == 'checkbox' or f.field_type == 'multiselect':
            vals = request.form.getlist(f.field_key)
            val = ", ".join(vals) if vals else ""
        else:
            val = request.form.get(f.field_key, '').strip()

        if f.is_required and not val:
            missing_required.append(f.label)
        extracted_data[f.field_key] = val

    if missing_required:
        flash(f"Please fill all required fields: {', '.join(missing_required)}", 'danger')
        return redirect(url_for('student.view_form', slug=slug))

    # Core student fields
    roll_number = extracted_data.get('roll_number', '').strip()
    student_name = extracted_data.get('student_name', '').strip()
    email = extracted_data.get('email', '').strip().lower()
    phone = extracted_data.get('phone', '')
    department = extracted_data.get('department', '')
    semester = extracted_data.get('semester', '6')
    batch = extracted_data.get('batch', '2026')
    
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
