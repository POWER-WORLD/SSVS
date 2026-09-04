import json
from collections import defaultdict
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort, send_file
from flask_login import login_required, current_user
from app.models import db
from app.models.form import Form, FormField, FieldOption
from app.models.submission import Submission, SubmissionValue
from app.models.platform_profile import PlatformProfile
from app.models.scoring import ScoreFormula, FormulaRule, LeaderboardEntry
from app.models.audit import ActivityLog
from app.utils.security import slugify
from app.utils.qrcode_gen import generate_qr_base64
from app.scoring_engine.default_presets import DEFAULT_PRESETS
from app.scoring_engine.formula_evaluator import FormulaEvaluator
from app.export.excel_exporter import ExcelExporter
from app.extractors import extract_all_profiles

forms_mgr_bp = Blueprint('forms_mgr', __name__, url_prefix='/forms')

@forms_mgr_bp.route('/')
@login_required
def list_forms():
    forms = current_user.forms.order_by(Form.created_at.desc()).all()
    return render_template('forms/list.html', forms=forms)

@forms_mgr_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_form():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        instructions = request.form.get('instructions', '').strip()
        theme_color = request.form.get('theme_color', '#4f46e5')
        
        if not title:
            flash('Assessment form title is required.', 'danger')
            return redirect(url_for('forms_mgr.list_forms'))

        slug = slugify(title)
        form = Form(
            title=title,
            description=description,
            instructions=instructions,
            theme_color=theme_color,
            slug=slug,
            teacher_id=current_user.id,
            is_published=True,  # Default ready to preview
            enable_leaderboard=True
        )
        db.session.add(form)
        db.session.flush()

        # Add standard default fields for every assessment form
        default_fields = [
            {'key': 'student_name', 'label': 'Full Name', 'type': 'text', 'req': True, 'order': 1, 'bind': 'student_name', 'sec': 'Personal Information'},
            {'key': 'roll_number', 'label': 'Roll Number / Student ID', 'type': 'text', 'req': True, 'order': 2, 'bind': 'roll_number', 'sec': 'Personal Information'},
            {'key': 'email', 'label': 'College Email Address', 'type': 'email', 'req': True, 'order': 3, 'bind': 'email', 'sec': 'Personal Information'},
            {'key': 'department', 'label': 'Department / Branch', 'type': 'dropdown', 'req': True, 'order': 4, 'bind': 'department', 'sec': 'Academic Details',
             'opts': ['Computer Science & Engineering', 'Information Technology', 'Electronics & Comm.', 'Electrical Eng.', 'Mechanical Eng.']},
            {'key': 'cgpa', 'label': 'Current CGPA (Out of 10.0)', 'type': 'decimal', 'req': True, 'order': 5, 'bind': 'cgpa', 'sec': 'Academic Details'},
            {'key': 'backlogs', 'label': 'Number of Active Backlogs', 'type': 'number', 'req': True, 'order': 6, 'bind': 'backlogs', 'sec': 'Academic Details'},
            {'key': 'leetcode_handle', 'label': 'LeetCode Profile URL / Username', 'type': 'url', 'req': True, 'order': 7, 'bind': 'leetcode_handle', 'sec': 'Coding Profiles', 'ph': 'https://leetcode.com/u/your_name/'},
            {'key': 'codechef_handle', 'label': 'CodeChef Profile URL / Username', 'type': 'url', 'req': False, 'order': 8, 'bind': 'codechef_handle', 'sec': 'Coding Profiles', 'ph': 'https://www.codechef.com/users/your_name'},
            {'key': 'github_handle', 'label': 'GitHub Profile URL / Username', 'type': 'url', 'req': False, 'order': 9, 'bind': 'github_handle', 'sec': 'Coding Profiles', 'ph': 'https://github.com/your_name'},
            {'key': 'codeforces_handle', 'label': 'Codeforces Handle (Optional)', 'type': 'text', 'req': False, 'order': 10, 'bind': 'codeforces_handle', 'sec': 'Coding Profiles', 'ph': 'tourist'}
        ]

        for df in default_fields:
            field = FormField(
                form_id=form.id,
                field_key=df['key'],
                label=df['label'],
                field_type=df['type'],
                is_required=df['req'],
                display_order=df['order'],
                platform_metric_binding=df['bind'],
                section_title=df['sec'],
                placeholder=df.get('ph', '')
            )
            db.session.add(field)
            db.session.flush()

            if 'opts' in df:
                for idx, opt_text in enumerate(df['opts']):
                    db.session.add(FieldOption(
                        field_id=field.id,
                        label=opt_text,
                        value=opt_text,
                        display_order=idx
                    ))

        # Create standard scoring formula
        std_preset = DEFAULT_PRESETS['standard_placement']
        formula = ScoreFormula(
            form_id=form.id,
            name=std_preset['name'],
            description=std_preset['description'],
            normalization_method=std_preset['normalization_method'],
            max_total_marks=std_preset['max_total_marks'],
            is_active=True
        )
        db.session.add(formula)
        db.session.flush()

        for r in std_preset['rules']:
            rule = FormulaRule(
                formula_id=formula.id,
                metric_key=r['metric_key'],
                display_label=r['display_label'],
                weight_percentage=r.get('weight_percentage', 10.0),
                max_marks=r.get('max_marks', 10.0),
                multiplier=r.get('multiplier', 1.0),
                penalty_per_unit=r.get('penalty_per_unit', 0.0),
                bonus_threshold=r.get('bonus_threshold', 0.0),
                bonus_marks=r.get('bonus_marks', 0.0),
                category=r.get('category', 'coding')
            )
            db.session.add(rule)

        db.session.add(ActivityLog(
            teacher_id=current_user.id,
            action='CREATE_FORM',
            description=f'Created new form "{form.title}"',
            ip_address=request.remote_addr
        ))
        db.session.commit()

        flash(f'Form "{form.title}" created! You can now customize fields and settings.', 'success')
        return redirect(url_for('forms_mgr.builder', form_id=form.id))

    return redirect(url_for('forms_mgr.list_forms'))

@forms_mgr_bp.route('/<int:form_id>/builder')
@login_required
def builder(form_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    fields = form.fields.order_by(FormField.display_order.asc()).all()
    fields_data = [f.to_dict(include_options=True) for f in fields]
    return render_template('forms/builder.html', form=form, fields=fields, fields_data=fields_data)

@forms_mgr_bp.route('/<int:form_id>/settings', methods=['GET', 'POST'])
@login_required
def settings(form_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    if request.method == 'POST':
        form.title = request.form.get('title', '').strip()
        form.description = request.form.get('description', '').strip()
        form.instructions = request.form.get('instructions', '').strip()
        form.theme_color = request.form.get('theme_color', '#4f46e5')
        
        deadline_str = request.form.get('deadline')
        if deadline_str:
            try:
                form.deadline = datetime.fromisoformat(deadline_str)
            except ValueError:
                pass
        else:
            form.deadline = None
            
        max_resp = request.form.get('max_responses')
        form.max_responses = int(max_resp) if max_resp and max_resp.isdigit() else None
        
        form.is_published = 'is_published' in request.form
        form.is_closed = 'is_closed' in request.form
        form.one_per_roll = 'one_per_roll' in request.form
        form.one_per_email = 'one_per_email' in request.form
        form.enable_leaderboard = 'enable_leaderboard' in request.form
        form.is_public = 'is_public' in request.form
        
        db.session.commit()
        flash('Form settings updated successfully.', 'success')
        return redirect(url_for('forms_mgr.settings', form_id=form.id))

    return render_template('forms/settings.html', form=form)

@forms_mgr_bp.route('/<int:form_id>/duplicate', methods=['POST'])
@login_required
def duplicate(form_id):
    original = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    
    new_slug = slugify(f"{original.title}-copy")
    clone = Form(
        title=f"{original.title} (Copy)",
        description=original.description,
        instructions=original.instructions,
        college_logo=original.college_logo,
        theme_color=original.theme_color,
        slug=new_slug,
        teacher_id=current_user.id,
        is_published=False,
        enable_leaderboard=original.enable_leaderboard
    )
    db.session.add(clone)
    db.session.flush()
    
    # Clone fields
    for f in original.fields.all():
        cloned_field = FormField(
            form_id=clone.id,
            field_key=f.field_key,
            label=f.label,
            field_type=f.field_type,
            placeholder=f.placeholder,
            help_text=f.help_text,
            is_required=f.is_required,
            default_value=f.default_value,
            section_title=f.section_title,
            display_order=f.display_order,
            platform_metric_binding=f.platform_metric_binding,
            validation_rules=f.validation_rules,
            conditional_rules=f.conditional_rules
        )
        db.session.add(cloned_field)
        db.session.flush()
        for opt in f.options.all():
            db.session.add(FieldOption(
                field_id=cloned_field.id,
                label=opt.label,
                value=opt.value,
                display_order=opt.display_order
            ))
            
    # Clone scoring formula
    orig_formula = original.formulas.filter_by(is_active=True).first()
    if orig_formula:
        cloned_formula = ScoreFormula(
            form_id=clone.id,
            name=orig_formula.name,
            description=orig_formula.description,
            normalization_method=orig_formula.normalization_method,
            max_total_marks=orig_formula.max_total_marks,
            is_active=True
        )
        db.session.add(cloned_formula)
        db.session.flush()
        for r in orig_formula.rules.all():
            db.session.add(FormulaRule(
                formula_id=cloned_formula.id,
                metric_key=r.metric_key,
                display_label=r.display_label,
                weight_percentage=r.weight_percentage,
                max_marks=r.max_marks,
                multiplier=r.multiplier,
                penalty_per_unit=r.penalty_per_unit,
                bonus_threshold=r.bonus_threshold,
                bonus_marks=r.bonus_marks,
                category=r.category
            ))

    db.session.commit()
    flash(f'Form duplicated as "{clone.title}".', 'success')
    return redirect(url_for('forms_mgr.list_forms'))

@forms_mgr_bp.route('/<int:form_id>/share')
@login_required
def share(form_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    public_url = url_for('student.view_form', slug=form.slug, _external=True)
    leaderboard_url = url_for('student.view_leaderboard', slug=form.slug, _external=True)
    qr_data_uri = generate_qr_base64(public_url)
    
    return render_template(
        'forms/share_qr.html',
        form=form,
        public_url=public_url,
        leaderboard_url=leaderboard_url,
        qr_data_uri=qr_data_uri
    )

def find_duplicate_handles(form_id):
    """Detects if multiple students share the same platform handles or roll numbers."""
    handle_map = defaultdict(list)
    
    profiles = db.session.query(
        PlatformProfile.platform_name,
        PlatformProfile.username,
        Submission.student_name,
        Submission.roll_number,
        Submission.id
    ).join(Submission, PlatformProfile.submission_id == Submission.id)\
     .filter(Submission.form_id == form_id).all()
        
    for p_name, u_name, s_name, r_num, s_id in profiles:
        u_clean = (u_name or '').strip().lower()
        if u_clean and u_clean not in ('unrated', 'none', 'n/a', 'na', ''):
            key = f"{p_name.capitalize()}: {u_clean}"
            handle_map[key].append({'name': s_name, 'roll': r_num, 'id': s_id})
            
    roll_map = defaultdict(list)
    subs = Submission.query.filter_by(form_id=form_id).all()
    for s in subs:
        r_clean = (s.roll_number or '').strip().lower()
        if r_clean:
            roll_map[r_clean].append({'name': s.student_name, 'roll': s.roll_number, 'id': s.id})

    duplicates = []
    for k, students in handle_map.items():
        if len(students) > 1:
            duplicates.append({
                'type': 'Shared Coding Profile',
                'handle': k,
                'students': students
            })
            
    for k, students in roll_map.items():
        if len(students) > 1:
            duplicates.append({
                'type': 'Duplicate Roll Number',
                'handle': f"Roll No: {students[0]['roll']}",
                'students': students
            })
            
    return duplicates

@forms_mgr_bp.route('/<int:form_id>/submissions')
@login_required
def submissions(form_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    dept_filter = request.args.get('department')
    search_q = request.args.get('q', '').strip().lower()
    status_filter = request.args.get('status')
    
    query = form.submissions
    if dept_filter:
        query = query.filter(Submission.department == dept_filter)
    if status_filter:
        query = query.filter(Submission.verification_status == status_filter)
    if search_q:
        query = query.filter(
            db.or_(
                Submission.student_name.ilike(f'%{search_q}%'),
                Submission.roll_number.ilike(f'%{search_q}%'),
                Submission.email.ilike(f'%{search_q}%')
            )
        )
        
    submissions_list = query.order_by(Submission.submitted_at.desc()).all()
    departments = [d[0] for d in db.session.query(Submission.department).filter(Submission.form_id == form.id, Submission.department != None).distinct().all()]
    duplicates = find_duplicate_handles(form.id)
    
    return render_template(
        'submissions/list.html',
        form=form,
        submissions=submissions_list,
        departments=departments,
        duplicates=duplicates
    )

@forms_mgr_bp.route('/<int:form_id>/submissions/<int:submission_id>')
@login_required
def submission_detail(form_id, submission_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    submission = Submission.query.filter_by(id=submission_id, form_id=form.id).first_or_404()
    profiles = submission.platform_profiles.all()
    score = submission.latest_score
    values = submission.values.all()
    
    return render_template(
        'submissions/detail.html',
        form=form,
        submission=submission,
        profiles=profiles,
        score=score,
        values=values
    )

@forms_mgr_bp.route('/<int:form_id>/submissions/<int:submission_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_submission(form_id, submission_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    submission = Submission.query.filter_by(id=submission_id, form_id=form.id).first_or_404()
    
    if request.method == 'POST':
        # Student Core Details
        submission.student_name = request.form.get('student_name', submission.student_name).strip()
        submission.roll_number = request.form.get('roll_number', submission.roll_number).strip()
        submission.email = request.form.get('email', submission.email).strip()
        submission.phone = request.form.get('phone', '').strip()
        submission.department = request.form.get('department', submission.department).strip()
        submission.semester = request.form.get('semester', submission.semester).strip()
        submission.batch = request.form.get('batch', submission.batch).strip()
        
        try:
            submission.cgpa = float(request.form.get('cgpa', submission.cgpa or 0.0))
        except (ValueError, TypeError):
            pass
            
        try:
            submission.backlogs = int(request.form.get('backlogs', submission.backlogs or 0))
        except (ValueError, TypeError):
            pass
            
        # Teacher Moderation
        submission.verification_status = request.form.get('verification_status', 'verified')
        submission.teacher_remarks = request.form.get('teacher_remarks', '').strip()
        try:
            submission.manual_score_adjustment = float(request.form.get('manual_score_adjustment', 0.0) or 0.0)
        except (ValueError, TypeError):
            submission.manual_score_adjustment = 0.0
            
        submission.last_modified_by = current_user.full_name or current_user.email
        submission.updated_at = datetime.utcnow()
        
        # Update custom form field values
        for val in submission.values.all():
            f_key = val.field.field_key if val.field else None
            if f_key and f_key in request.form:
                val.value_text = request.form.get(f_key, '').strip()
                
        # Update platform handles
        platforms = ['leetcode', 'codechef', 'codeforces', 'github', 'hackerrank', 'gfg', 'atcoder', 'interviewbit', 'kaggle']
        profile_map = {p.platform_name.lower(): p for p in submission.platform_profiles.all()}
        
        for p_name in platforms:
            input_handle = request.form.get(f'handle_{p_name}', '').strip()
            if input_handle:
                if p_name in profile_map:
                    prof = profile_map[p_name]
                    if prof.username != input_handle:
                        prof.username = input_handle
                else:
                    new_prof = PlatformProfile(
                        submission_id=submission.id,
                        platform_name=p_name,
                        username=input_handle,
                        extraction_status='pending'
                    )
                    db.session.add(new_prof)
                    
        db.session.commit()
        
        # Recalculate score and rankings immediately if selected or by default
        recalc = request.form.get('recalculate_score') in ('on', '1', 'true', True)
        if recalc:
            active_formula = form.formulas.filter_by(is_active=True).first()
            if active_formula:
                FormulaEvaluator.evaluate_submission(submission, active_formula)
                FormulaEvaluator.update_form_ranks_and_leaderboard(form.id)
                
        # Activity log
        log = ActivityLog(
            teacher_id=current_user.id,
            form_id=form.id,
            action='edit_submission',
            description=f'Updated collected data for {submission.student_name} ({submission.roll_number})',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'Candidate data for {submission.student_name} has been updated successfully!', 'success')
        return redirect(url_for('forms_mgr.submission_detail', form_id=form.id, submission_id=submission.id))
        
    # GET
    profiles = {p.platform_name.lower(): p for p in submission.platform_profiles.all()}
    values = submission.values.all()
    score = submission.latest_score
    return render_template(
        'submissions/edit.html',
        form=form,
        submission=submission,
        profiles=profiles,
        values=values,
        score=score
    )

@forms_mgr_bp.route('/<int:form_id>/submissions/<int:submission_id>/delete', methods=['POST'])
@login_required
def delete_submission(form_id, submission_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    submission = Submission.query.filter_by(id=submission_id, form_id=form.id).first_or_404()
    name = submission.student_name
    db.session.delete(submission)
    db.session.commit()
    FormulaEvaluator.update_form_ranks_and_leaderboard(form.id)
    flash(f'Submission for {name} has been deleted and cohort ranks updated.', 'info')
    return redirect(url_for('forms_mgr.submissions', form_id=form.id))

@forms_mgr_bp.route('/<int:form_id>/export/custom-excel', methods=['GET', 'POST'])
@login_required
def export_custom_excel(form_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    
    # Selected submissions
    selected_ids = request.form.getlist('selected_ids') or request.args.getlist('selected_ids')
    if not selected_ids:
        raw_ids = request.form.get('selected_ids_str') or request.args.get('selected_ids_str', '')
        if raw_ids:
            selected_ids = [s.strip() for s in raw_ids.split(',') if s.strip()]
            
    # Selected columns
    selected_cols = request.form.getlist('columns') or request.args.getlist('columns')
    if not selected_cols:
        raw_cols = request.form.get('columns_str') or request.args.get('columns_str', '')
        if raw_cols:
            selected_cols = [c.strip() for c in raw_cols.split(',') if c.strip()]
            
    stream = ExcelExporter.generate_custom_export(form, submission_ids=selected_ids, column_keys=selected_cols)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M')
    filename = f"SSVS_Custom_Export_{form.slug}_{timestamp}.xlsx"
    
    return send_file(
        stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@forms_mgr_bp.route('/<int:form_id>/submissions/batch-action', methods=['POST'])
@login_required
def batch_action(form_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    action = request.form.get('action')
    selected_ids = request.form.getlist('selected_ids')
    
    if not selected_ids:
        raw_ids = request.form.get('selected_ids_str', '')
        if raw_ids:
            selected_ids = [s.strip() for s in raw_ids.split(',') if s.strip()]
            
    if not selected_ids:
        flash('Please select one or more candidates to execute this batch action.', 'warning')
        return redirect(url_for('forms_mgr.submissions', form_id=form.id))
        
    clean_ids = []
    for sid in selected_ids:
        try:
            clean_ids.append(int(sid))
        except (ValueError, TypeError):
            pass
            
    subs = Submission.query.filter(Submission.id.in_(clean_ids), Submission.form_id == form.id).all()
    
    if action == 'mark_verified':
        for s in subs:
            s.verification_status = 'verified'
        db.session.commit()
        flash(f'Marked {len(subs)} selected candidate(s) as Verified.', 'success')
    elif action == 'mark_shortlisted':
        for s in subs:
            s.verification_status = 'shortlisted'
        db.session.commit()
        flash(f'Marked {len(subs)} selected candidate(s) as Shortlisted for placements.', 'success')
    elif action == 'mark_flagged':
        for s in subs:
            s.verification_status = 'flagged'
        db.session.commit()
        flash(f'Flagged {len(subs)} candidate submission(s) for review.', 'warning')
    elif action == 'recalculate':
        active_formula = form.formulas.filter_by(is_active=True).first()
        if active_formula:
            for s in subs:
                FormulaEvaluator.evaluate_submission(s, active_formula)
            FormulaEvaluator.update_form_ranks_and_leaderboard(form.id)
            flash(f'Recalculated scores and updated rankings for {len(subs)} candidate(s).', 'success')
    elif action == 'delete':
        count = len(subs)
        for s in subs:
            db.session.delete(s)
        db.session.commit()
        FormulaEvaluator.update_form_ranks_and_leaderboard(form.id)
        flash(f'Deleted {count} selected submission(s).', 'info')
    else:
        flash(f'Unknown batch action "{action}".', 'danger')
        
    return redirect(url_for('forms_mgr.submissions', form_id=form.id))

@forms_mgr_bp.route('/<int:form_id>/compare')
@login_required
def compare_submissions(form_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    raw_ids = request.args.get('ids', '')
    id_list = []
    for x in raw_ids.split(','):
        try:
            id_list.append(int(x.strip()))
        except (ValueError, TypeError):
            pass
            
    if not id_list:
        flash('Please select at least 2 candidates to compare.', 'info')
        return redirect(url_for('forms_mgr.submissions', form_id=form.id))
        
    subs = Submission.query.filter(Submission.id.in_(id_list), Submission.form_id == form.id).all()
    if len(subs) < 2:
        flash('Please select at least 2 candidates for comparison.', 'warning')
        return redirect(url_for('forms_mgr.submissions', form_id=form.id))

    # Pre-extract comparison metrics
    candidates_data = []
    for s in subs:
        score = s.latest_score
        prof_map = {p.platform_name.lower(): p for p in s.platform_profiles.all()}
        lc = prof_map.get('leetcode')
        cc = prof_map.get('codechef')
        cf = prof_map.get('codeforces')
        gh = prof_map.get('github')
        atc = prof_map.get('atcoder')
        ib = prof_map.get('interviewbit')
        kg = prof_map.get('kaggle')
        
        candidates_data.append({
            'id': s.id,
            'name': s.student_name,
            'roll': s.roll_number,
            'dept': s.department,
            'cgpa': s.cgpa or 0.0,
            'backlogs': s.backlogs or 0,
            'total_score': score.total_score if score else 0.0,
            'rank': score.rank if score else '—',
            'grade': score.grade if score else '—',
            'percentile': score.percentile if score else 0.0,
            'status': getattr(s, 'verification_status', 'verified') or 'verified',
            'remarks': getattr(s, 'teacher_remarks', '') or '',
            # Metrics
            'leetcode_solved': lc.problems_solved if lc else 0,
            'leetcode_rating': lc.contest_rating if lc else 0,
            'codechef_rating': cc.contest_rating if cc else 0,
            'codeforces_rating': cf.contest_rating if cf else 0,
            'github_repos': gh.problems_solved if gh else 0,
            'github_stars': (gh.raw_data or {}).get('stars_earned', 0) if gh else 0,
            'atcoder_rating': atc.contest_rating if atc else 0,
            'interviewbit_score': ib.contest_rating if ib else 0,
            'kaggle_medals': kg.stars_or_badges if kg else 0,
        })
        
    return render_template(
        'submissions/compare.html',
        form=form,
        candidates=candidates_data
    )


@forms_mgr_bp.route('/<int:form_id>/formula', methods=['GET', 'POST'])
@login_required
def formula_builder(form_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    formula = form.formulas.filter_by(is_active=True).first()
    
    if request.method == 'POST':
        # Update formula parameters
        formula.name = request.form.get('name', 'Custom Formula').strip()
        formula.normalization_method = request.form.get('normalization_method', 'min_max')
        formula.max_total_marks = float(request.form.get('max_total_marks', 100.0))
        
        # Read dynamic rules from form
        rule_keys = request.form.getlist('rule_metric_key')
        rule_labels = request.form.getlist('rule_display_label')
        rule_weights = request.form.getlist('rule_weight')
        rule_maxs = request.form.getlist('rule_max_marks')
        rule_penalties = request.form.getlist('rule_penalty')
        rule_categories = request.form.getlist('rule_category')
        
        # Clear existing rules and re-add
        FormulaRule.query.filter_by(formula_id=formula.id).delete()
        
        for i in range(len(rule_keys)):
            m_key = rule_keys[i].strip()
            if not m_key:
                continue
            cat = rule_categories[i] if i < len(rule_categories) else 'coding'
            w = float(rule_weights[i]) if i < len(rule_weights) and rule_weights[i] else 10.0
            mx = float(rule_maxs[i]) if i < len(rule_maxs) and rule_maxs[i] else 10.0
            pen = float(rule_penalties[i]) if i < len(rule_penalties) and rule_penalties[i] else 0.0
            
            mult = 1.0
            if m_key == 'cgpa':
                mult = mx / 10.0
            elif m_key == 'leetcode_solved':
                mult = mx / 300.0
            elif m_key == 'leetcode_rating':
                mult = mx / 1800.0
            elif m_key == 'codechef_rating':
                mult = mx / 1700.0
            elif m_key == 'codeforces_rating':
                mult = mx / 1600.0
                
            rule = FormulaRule(
                formula_id=formula.id,
                metric_key=m_key,
                display_label=rule_labels[i] if i < len(rule_labels) else m_key.title(),
                weight_percentage=w,
                max_marks=mx,
                multiplier=mult,
                penalty_per_unit=pen,
                category=cat
            )
            db.session.add(rule)
            
        db.session.commit()
        
        # Recalculate scores with updated formula
        FormulaEvaluator.update_form_ranks_and_leaderboard(form.id)
        
        flash('Scoring formula saved and all student rankings recalculated!', 'success')
        return redirect(url_for('forms_mgr.formula_builder', form_id=form.id))

    rules = formula.rules.all() if formula else []
    return render_template('scoring/formula_builder.html', form=form, formula=formula, rules=rules, presets=DEFAULT_PRESETS)

@forms_mgr_bp.route('/<int:form_id>/formula/apply-preset/<preset_name>', methods=['POST'])
@login_required
def apply_preset(form_id, preset_name):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    if preset_name not in DEFAULT_PRESETS:
        flash('Invalid preset selected.', 'danger')
        return redirect(url_for('forms_mgr.formula_builder', form_id=form.id))
        
    preset = DEFAULT_PRESETS[preset_name]
    formula = form.formulas.filter_by(is_active=True).first()
    if not formula:
        formula = ScoreFormula(form_id=form.id, is_active=True)
        db.session.add(formula)
        db.session.flush()

    formula.name = preset['name']
    formula.description = preset['description']
    formula.normalization_method = preset['normalization_method']
    formula.max_total_marks = preset['max_total_marks']
    
    FormulaRule.query.filter_by(formula_id=formula.id).delete()
    for r in preset['rules']:
        rule = FormulaRule(
            formula_id=formula.id,
            metric_key=r['metric_key'],
            display_label=r['display_label'],
            weight_percentage=r.get('weight_percentage', 10.0),
            max_marks=r.get('max_marks', 10.0),
            multiplier=r.get('multiplier', 1.0),
            penalty_per_unit=r.get('penalty_per_unit', 0.0),
            bonus_threshold=r.get('bonus_threshold', 0.0),
            bonus_marks=r.get('bonus_marks', 0.0),
            category=r.get('category', 'coding')
        )
        db.session.add(rule)
        
    db.session.commit()
    FormulaEvaluator.update_form_ranks_and_leaderboard(form.id)
    
    flash(f'Applied preset "{preset["name"]}"! Leaderboard rankings recalculated.', 'success')
    return redirect(url_for('forms_mgr.formula_builder', form_id=form.id))

@forms_mgr_bp.route('/<int:form_id>/delete', methods=['POST'])
@login_required
def delete_form(form_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    title = form.title
    db.session.delete(form)
    db.session.commit()
    flash(f'Form "{title}" and all related submissions have been deleted.', 'info')
    return redirect(url_for('forms_mgr.list_forms'))
