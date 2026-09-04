from flask import Blueprint, render_template, send_file, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models.form import Form
from app.models.submission import Submission
from app.models.scoring import LeaderboardEntry, CalculatedScore
from app.export.excel_exporter import ExcelExporter

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics_bp.route('/<int:form_id>')
@login_required
def dashboard(form_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    entries = LeaderboardEntry.query.filter_by(form_id=form.id).order_by(LeaderboardEntry.rank.asc()).all()
    submissions = form.submissions.all()
    
    total_count = len(entries)
    scores = [e.total_score for e in entries] if entries else []
    cgpas = [e.cgpa for e in entries if e.cgpa] if entries else []
    
    avg_score = round(sum(scores) / total_count, 1) if total_count else 0.0
    highest_score = round(max(scores), 1) if scores else 0.0
    lowest_score = round(min(scores), 1) if scores else 0.0
    median_score = round(sorted(scores)[total_count // 2], 1) if total_count else 0.0
    avg_cgpa = round(sum(cgpas) / len(cgpas), 2) if cgpas else 0.0
    
    # 1. Score histogram buckets: 0-20, 21-40, 41-60, 61-80, 81-100
    histogram = [0, 0, 0, 0, 0]
    for s in scores:
        if s <= 20:
            histogram[0] += 1
        elif s <= 40:
            histogram[1] += 1
        elif s <= 60:
            histogram[2] += 1
        elif s <= 80:
            histogram[3] += 1
        else:
            histogram[4] += 1

    # 2. Platform participation counts
    platform_counts = {'LeetCode': 0, 'CodeChef': 0, 'Codeforces': 0, 'GitHub': 0, 'HackerRank': 0}
    for sub in submissions:
        for p in sub.platform_profiles.all():
            pn = p.platform_name.lower()
            if 'leetcode' in pn:
                platform_counts['LeetCode'] += 1
            elif 'codechef' in pn:
                platform_counts['CodeChef'] += 1
            elif 'codeforces' in pn:
                platform_counts['Codeforces'] += 1
            elif 'github' in pn:
                platform_counts['GitHub'] += 1
            elif 'hackerrank' in pn:
                platform_counts['HackerRank'] += 1

    # 3. Department averages
    dept_scores = {}
    for e in entries:
        dept = e.department or 'Unspecified'
        if dept not in dept_scores:
            dept_scores[dept] = []
        dept_scores[dept].append(e.total_score)
        
    dept_labels = list(dept_scores.keys())
    dept_avgs = [round(sum(v) / len(v), 1) for v in dept_scores.values()]

    # 4. Top 10 Coders for Bar Chart
    top_coders = entries[:10]
    top_coder_names = [e.student_name for e in top_coders]
    top_coder_scores = [e.total_score for e in top_coders]

    # 5. CGPA vs Score scatter points
    scatter_points = [{'x': round(e.cgpa, 2), 'y': round(e.total_score, 1), 'name': e.student_name} for e in entries if e.cgpa]

    return render_template(
        'analytics/dashboard.html',
        form=form,
        total_count=total_count,
        avg_score=avg_score,
        highest_score=highest_score,
        lowest_score=lowest_score,
        median_score=median_score,
        avg_cgpa=avg_cgpa,
        histogram=histogram,
        platform_counts=platform_counts,
        dept_labels=dept_labels,
        dept_avgs=dept_avgs,
        top_coder_names=top_coder_names,
        top_coder_scores=top_coder_scores,
        scatter_points=scatter_points,
        entries=entries
    )

@analytics_bp.route('/<int:form_id>/export/excel')
@login_required
def export_excel(form_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    if form.submissions.count() == 0:
        flash('No student submissions found to export.', 'warning')
        return redirect(url_for('forms_mgr.submissions', form_id=form.id))

    excel_stream = ExcelExporter.generate_form_report(form)
    clean_title = "".join(c for c in form.title if c.isalnum() or c in (' ', '_', '-')).rstrip()
    filename = f"SSVS_{clean_title}_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"
    
    return send_file(
        excel_stream,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
