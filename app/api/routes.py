import re
from flask import Blueprint, jsonify, request, abort, current_app
from flask_login import login_required, current_user
from app.models import db
from app.models.form import Form, FormField, FieldOption
from app.models.submission import Submission, SubmissionValue
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
        return jsonify({'status': 'error', 'message': 'Invalid payload: fields array required'}), 400

    fields_data = data['fields']
    if not isinstance(fields_data, list):
        return jsonify({'status': 'error', 'message': 'Fields must be a list'}), 400

    try:
        # 1. Track valid existing IDs
        incoming_ids = []
        for f in fields_data:
            fid = f.get('id')
            if fid is not None:
                try:
                    incoming_ids.append(int(fid))
                except (ValueError, TypeError):
                    pass

        # 2. Identify fields to delete
        if incoming_ids:
            fields_to_delete = FormField.query.filter(
                FormField.form_id == form.id,
                ~FormField.id.in_(incoming_ids)
            ).all()
        else:
            fields_to_delete = FormField.query.filter_by(form_id=form.id).all()

        field_ids_to_delete = [f.id for f in fields_to_delete]
        if field_ids_to_delete:
            # Delete child FieldOptions first to prevent ForeignKeyViolation
            FieldOption.query.filter(FieldOption.field_id.in_(field_ids_to_delete)).delete(synchronize_session=False)
            # Delete child SubmissionValues if any
            SubmissionValue.query.filter(SubmissionValue.field_id.in_(field_ids_to_delete)).delete(synchronize_session=False)
            # Safely delete the form fields
            FormField.query.filter(FormField.id.in_(field_ids_to_delete)).delete(synchronize_session=False)

        # 3. Create or update fields
        seen_keys = set()
        saved_fields = []

        for order_idx, f_data in enumerate(fields_data):
            field_id = None
            if f_data.get('id'):
                try:
                    field_id = int(f_data['id'])
                except (ValueError, TypeError):
                    field_id = None

            field = None
            if field_id:
                field = FormField.query.filter_by(id=field_id, form_id=form.id).first()
            
            if not field:
                field = FormField(form_id=form.id)
                db.session.add(field)

            # Sanitize and ensure unique field_key
            raw_key = (f_data.get('field_key') or f_data.get('label') or f"field_{order_idx + 1}").strip()
            clean_key = re.sub(r'[^a-zA-Z0-9_]', '_', raw_key).strip('_') or f"field_{order_idx + 1}"
            unique_key = clean_key
            suffix = 1
            while unique_key in seen_keys:
                suffix += 1
                unique_key = f"{clean_key}_{suffix}"
            seen_keys.add(unique_key)

            field.field_key = unique_key
            field.label = f_data.get('label', 'Untitled Field')
            field.field_type = f_data.get('field_type', 'text')
            field.placeholder = f_data.get('placeholder', '')
            field.help_text = f_data.get('help_text', '')
            field.is_required = bool(f_data.get('is_required', False))
            field.default_value = f_data.get('default_value', '')
            field.section_title = f_data.get('section_title', 'General')
            field.display_order = order_idx + 1
            field.platform_metric_binding = f_data.get('platform_metric_binding') or None
            field.validation_rules = f_data.get('validation_rules') or {}

            db.session.flush()

            # Update options if applicable (for dropdown or custom choices)
            raw_options = f_data.get('options')
            if raw_options is not None:
                FieldOption.query.filter_by(field_id=field.id).delete()
                for opt_idx, opt in enumerate(raw_options):
                    if isinstance(opt, dict):
                        lbl = str(opt.get('label', '')).strip()
                        val = str(opt.get('value', lbl)).strip()
                    else:
                        lbl = str(opt).strip()
                        val = lbl
                    if lbl:
                        db.session.add(FieldOption(
                            field_id=field.id,
                            label=lbl,
                            value=val,
                            display_order=opt_idx
                        ))

            saved_fields.append(field)

        db.session.commit()

        # Return updated serialized fields with fresh database IDs
        return jsonify({
            'status': 'success',
            'message': 'Form fields successfully saved!',
            'fields': [f.to_dict(include_options=True) for f in saved_fields]
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error saving form fields: %s", e)
        return jsonify({
            'status': 'error',
            'message': f"Failed to save form fields: {str(e)}"
        }), 500

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
