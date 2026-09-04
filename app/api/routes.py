from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from app.models import db
from app.models.form import Form, FormField, FieldOption
from app.models.submission import Submission
from app.models.scoring import LeaderboardEntry
from app.extractors import extract_all_profiles
from app.scoring_engine.formula_evaluator import FormulaEvaluator

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/form/<int:form_id>/fields', methods=['GET'])
@login_required
def get_form_fields(form_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    fields = form.fields.order_by(FormField.display_order.asc()).all()
    return jsonify({
        'status': 'success',
        'form': form.to_dict(),
        'fields': [f.to_dict(include_options=True) for f in fields]
    })

@api_bp.route('/form/<int:form_id>/save-fields', methods=['POST'])
@login_required
def save_form_fields(form_id):
    form = Form.query.filter_by(id=form_id, teacher_id=current_user.id).first_or_404()
    data = request.get_json()
    if not data or 'fields' not in data:
        return jsonify({'status': 'error', 'message': 'Invalid payload'}), 400

    fields_data = data['fields']
    
    # Track existing IDs
    incoming_ids = [f.get('id') for f in fields_data if f.get('id')]
    
    # Delete removed fields
    FormField.query.filter(FormField.form_id == form.id, ~FormField.id.in_(incoming_ids)).delete(synchronize_session=False)

    for order_idx, f_data in enumerate(fields_data):
        field_id = f_data.get('id')
        if field_id:
            field = FormField.query.filter_by(id=field_id, form_id=form.id).first()
        else:
            field = FormField(form_id=form.id)
            db.session.add(field)

        field.field_key = f_data.get('field_key') or f"field_{order_idx + 1}"
        field.label = f_data.get('label', 'Untitled Field')
        field.field_type = f_data.get('field_type', 'text')
        field.placeholder = f_data.get('placeholder', '')
        field.help_text = f_data.get('help_text', '')
        field.is_required = bool(f_data.get('is_required', False))
        field.default_value = f_data.get('default_value', '')
        field.section_title = f_data.get('section_title', 'General')
        field.display_order = order_idx + 1
        field.platform_metric_binding = f_data.get('platform_metric_binding')
        field.validation_rules = f_data.get('validation_rules', {})

        db.session.flush()

        # Update options if applicable
        if f_data.get('options'):
            FieldOption.query.filter_by(field_id=field.id).delete()
            for opt_idx, opt in enumerate(f_data['options']):
                lbl = opt.get('label') if isinstance(opt, dict) else str(opt)
                val = opt.get('value', lbl) if isinstance(opt, dict) else str(opt)
                db.session.add(FieldOption(
                    field_id=field.id,
                    label=lbl,
                    value=val,
                    display_order=opt_idx
                ))

    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Form fields successfully updated!'})

@api_bp.route('/submission/<uuid>/status', methods=['GET'])
def get_submission_status(uuid):
    submission = Submission.query.filter_by(uuid=uuid).first_or_404()
    score = submission.latest_score
    profiles = [p.to_dict() for p in submission.platform_profiles.all()]
    
    return jsonify({
        'status': submission.status,
        'student_name': submission.student_name,
        'roll_number': submission.roll_number,
        'cgpa': submission.cgpa,
        'backlogs': submission.backlogs,
        'score': score.to_dict() if score else None,
        'profiles': profiles,
        'error': submission.error_message
    })

@api_bp.route('/profile/test-extract', methods=['POST'])
@login_required
def test_extract_profile():
    """Allows teachers to preview statistics for any handle or profile URL."""
    data = request.get_json() or {}
    platform = data.get('platform', 'leetcode').lower()
    handle = data.get('handle', '').strip()
    
    if not handle:
        return jsonify({'status': 'error', 'message': 'Handle or URL is required'}), 400
        
    stats = extract_all_profiles({platform: handle})
    return jsonify({
        'status': 'success',
        'platform': platform,
        'handle': handle,
        'data': stats.to_dict().get(platform)
    })
