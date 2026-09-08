import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db
from app.models.user import Teacher
from app.models.audit import ActivityLog
from app.models.otp import EmailOTP
from app.auth.forms import (
    LoginForm, RegistrationForm, ForgotPasswordForm, 
    ProfileForm, VerifyOTPForm, ResetPasswordForm, DeleteAccountForm
)
from app.utils.email_service import send_otp_code_email

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Teacher login: direct email & password authentication (no OTP required for verified accounts)."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.overview'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = Teacher.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'danger')
                return render_template('auth/login.html', form=form)
                
            # If teacher registered but hasn't completed email verification, prompt for registration OTP
            if not user.email_verified:
                can_resend, _ = EmailOTP.can_resend(user.email, 'registration', cooldown_seconds=60)
                if can_resend:
                    _, raw_code = EmailOTP.create_otp(user.email, purpose='registration', validity_minutes=10)
                    send_otp_code_email(user.email, raw_code, purpose='registration', validity_minutes=10)
                
                session['pending_verification_email'] = user.email
                session['pending_verification_purpose'] = 'registration'
                flash(f'Your email is not verified yet. A verification code has been dispatched to {user.email}. Please verify your account to continue.', 'warning')
                return redirect(url_for('auth.verify_otp', email=user.email, purpose='registration'))
            
            # Direct sign-in for verified accounts (NO OTP REQUIRED)
            login_user(user, remember=form.remember.data)
            
            db.session.add(ActivityLog(
                teacher_id=user.id,
                action='LOGIN_SUCCESS',
                description=f'Teacher {user.full_name} signed in successfully',
                ip_address=request.remote_addr
            ))
            db.session.commit()
            
            flash(f'Welcome back, Prof. {user.full_name}!', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard.overview'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
            
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Teacher registration: saves teacher profile and dispatches SMTP OTP."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.overview'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        existing_user = Teacher.query.filter_by(email=email).first()
        
        if existing_user and not existing_user.email_verified:
            user = existing_user
            user.full_name = form.full_name.data.strip()
            user.college_name = form.college_name.data.strip()
            user.department = form.department.data.strip()
            user.designation = form.designation.data.strip()
            user.phone = form.phone.data.strip() if form.phone.data else None
            user.set_password(form.password.data)
        else:
            user = Teacher(
                email=email,
                full_name=form.full_name.data.strip(),
                college_name=form.college_name.data.strip(),
                department=form.department.data.strip(),
                designation=form.designation.data.strip(),
                phone=form.phone.data.strip() if form.phone.data else None,
                is_active=True,
                email_verified=False
            )
            user.set_password(form.password.data)
            db.session.add(user)

        db.session.commit()
        
        _, raw_code = EmailOTP.create_otp(user.email, purpose='registration', validity_minutes=10)
        sent, msg = send_otp_code_email(user.email, raw_code, purpose='registration', validity_minutes=10)
        
        session['pending_verification_email'] = user.email
        session['pending_verification_purpose'] = 'registration'
        
        if sent:
            flash(f'Registration submitted! A 6-digit verification code has been sent to {user.email}.', 'info')
        else:
            flash(f'Account created, but email notice: {msg}', 'warning')
            
        return redirect(url_for('auth.verify_otp', email=user.email, purpose='registration'))
        
    return render_template('auth/register.html', form=form)

@auth_bp.route('/verify-otp', endpoint='verify_otp', methods=['GET', 'POST'])
@auth_bp.route('/verify-email', endpoint='verify_email', methods=['GET', 'POST'])
@auth_bp.route('/verify-login', endpoint='verify_login', methods=['GET', 'POST'])
def verify_otp():
    """Unified OTP verification endpoint for teacher registration and login."""
    email = request.args.get('email') or session.get('pending_verification_email')
    purpose = request.args.get('purpose') or session.get('pending_verification_purpose', 'registration')
    
    if not email:
        flash('No pending verification request found. Please log in or register.', 'warning')
        return redirect(url_for('auth.login'))

    user = Teacher.query.filter_by(email=email.lower().strip()).first()
    if not user:
        flash('Account not found. Please register.', 'danger')
        return redirect(url_for('auth.register'))

    form = VerifyOTPForm()
    if form.validate_on_submit():
        entered_code = form.otp_code.data.strip()
        success, message = EmailOTP.verify_otp(email, purpose, entered_code)
        
        if success:
            user.email_verified = True
            user.is_active = True
            remember = session.get('pending_login_remember', False)
            next_page = session.get('pending_login_next')
            
            login_user(user, remember=remember)
            db.session.add(ActivityLog(
                teacher_id=user.id,
                action='VERIFY_OTP_SUCCESS',
                description=f'Verified OTP for {purpose} from {request.remote_addr}',
                ip_address=request.remote_addr
            ))
            db.session.commit()

            session.pop('pending_verification_email', None)
            session.pop('pending_verification_purpose', None)
            session.pop('pending_login_remember', None)
            session.pop('pending_login_next', None)

            flash(f'Verification successful! Welcome, Prof. {user.full_name}.', 'success')
            return redirect(next_page or url_for('dashboard.overview'))
        else:
            flash(message, 'danger')

    can_resend, remaining_cooldown = EmailOTP.can_resend(email, purpose, cooldown_seconds=60)
    return render_template('auth/verify_email.html', 
                           form=form, 
                           email=email, 
                           purpose=purpose, 
                           can_resend=can_resend, 
                           cooldown=remaining_cooldown)

@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resends verification OTP with 60-second cooldown."""
    is_json = request.is_json
    data = request.get_json(silent=True) or request.form
    
    email = (data.get('email') or session.get('pending_verification_email', '')).lower().strip()
    purpose = data.get('purpose') or session.get('pending_verification_purpose', 'registration')
    
    if not email:
        msg = "Email address is required to resend verification code."
        return jsonify({'success': False, 'message': msg}) if is_json else (flash(msg, 'danger') or redirect(url_for('auth.login')))

    can_resend, remaining = EmailOTP.can_resend(email, purpose, cooldown_seconds=60)
    if not can_resend:
        msg = f"Please wait {remaining} seconds before requesting another code."
        if is_json:
            return jsonify({'success': False, 'message': msg, 'cooldown': remaining}), 429
        flash(msg, 'warning')
        return redirect(url_for('auth.verify_otp', email=email, purpose=purpose))

    _, raw_code = EmailOTP.create_otp(email, purpose=purpose, validity_minutes=10)
    sent, err_or_id = send_otp_code_email(email, raw_code, purpose=purpose, validity_minutes=10)

    if sent:
        msg = f"A fresh 6-digit code has been dispatched to {email}."
        if is_json:
            return jsonify({'success': True, 'message': msg, 'cooldown': 60})
        flash(msg, 'success')
    else:
        msg = f"Unable to dispatch email: {err_or_id}"
        if is_json:
            return jsonify({'success': False, 'message': msg, 'cooldown': 0}), 500
        flash(msg, 'danger')

    return redirect(url_for('auth.verify_otp', email=email, purpose=purpose))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data.strip()
        current_user.college_name = form.college_name.data.strip()
        current_user.department = form.department.data.strip()
        current_user.designation = form.designation.data.strip()
        current_user.phone = form.phone.data.strip() if form.phone.data else None
        
        db.session.add(ActivityLog(
            teacher_id=current_user.id,
            action='UPDATE_PROFILE',
            description='Updated personal profile information',
            ip_address=request.remote_addr
        ))
        db.session.commit()
        
        flash('Your profile has been updated successfully.', 'success')
        return redirect(url_for('auth.profile'))
        
    delete_form = DeleteAccountForm()
    logs = current_user.activity_logs.order_by(ActivityLog.created_at.desc()).limit(10).all()
    return render_template('auth/profile.html', form=form, delete_form=delete_form, logs=logs)

@auth_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Permanently delete teacher account and purge all associated data and files."""
    form = DeleteAccountForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.password.data):
            flash('Incorrect password. Account deletion cancelled.', 'danger')
            return redirect(url_for('auth.profile'))

        teacher = current_user
        teacher_email = teacher.email
        teacher_name = teacher.full_name

        # 1. Clean up uploaded files (QR codes, logos, student submission uploads)
        try:
            for form_obj in teacher.forms.all():
                if form_obj.qr_code_path:
                    qr_file = os.path.join(current_app.root_path, '..', form_obj.qr_code_path)
                    if os.path.exists(qr_file):
                        try:
                            os.remove(qr_file)
                        except OSError:
                            pass

                if form_obj.college_logo and 'uploads/' in form_obj.college_logo:
                    logo_file = os.path.join(current_app.root_path, '..', form_obj.college_logo)
                    if os.path.exists(logo_file):
                        try:
                            os.remove(logo_file)
                        except OSError:
                            pass

                for sub in form_obj.submissions.all():
                    for val in sub.values.all():
                        if val.value_text and val.value_text.startswith('uploads/'):
                            up_file = os.path.join(current_app.root_path, '..', val.value_text)
                            if os.path.exists(up_file):
                                try:
                                    os.remove(up_file)
                                except OSError:
                                    pass
        except Exception:
            pass

        # 2. Delete OTP tokens associated with this teacher's email
        EmailOTP.query.filter_by(email=teacher_email.lower().strip()).delete()

        # 3. Delete Leaderboard entries associated with teacher's forms
        from app.models.scoring import LeaderboardEntry
        for form_obj in teacher.forms.all():
            LeaderboardEntry.query.filter_by(form_id=form_obj.id).delete()

        # 4. Delete Teacher record (cascades all forms, fields, submissions, values, profiles, formulas, and activity logs)
        db.session.delete(teacher)
        db.session.commit()

        # 5. Log user out and purge session
        logout_user()
        session.clear()

        flash(f'Account for Prof. {teacher_name} and all related assessment data have been permanently deleted.', 'info')
        return redirect(url_for('auth.register'))

    for _, errors in form.errors.items():
        for error in errors:
            flash(f'{error}', 'danger')
    return redirect(url_for('auth.profile'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.overview'))
        
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = Teacher.query.filter_by(email=email).first()
        
        if user:
            can_resend, _ = EmailOTP.can_resend(email, 'password_reset', cooldown_seconds=60)
            if can_resend:
                _, raw_code = EmailOTP.create_otp(email, purpose='password_reset', validity_minutes=10)
                send_otp_code_email(email, raw_code, purpose='password_reset', validity_minutes=10)
            flash(f'A 6-digit password reset code has been sent to {email}.', 'info')
            return redirect(url_for('auth.reset_password', email=email))
        else:
            flash(f'If an account exists with {email}, a password reset code has been sent.', 'info')
            return redirect(url_for('auth.reset_password', email=email))

    return render_template('auth/forgot_password.html', form=form)

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.overview'))
        
    email = request.args.get('email') or request.form.get('email', '')
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        email = (request.form.get('email') or email).lower().strip()
        entered_code = form.otp_code.data.strip()
        
        success, message = EmailOTP.verify_otp(email, 'password_reset', entered_code)
        if success:
            user = Teacher.query.filter_by(email=email).first()
            if user:
                user.set_password(form.password.data)
                user.email_verified = True
                db.session.add(ActivityLog(
                    teacher_id=user.id,
                    action='PASSWORD_RESET',
                    description='Password was reset via OTP verification',
                    ip_address=request.remote_addr
                ))
                db.session.commit()
                flash('Your password has been updated successfully! Please sign in with your new password.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Account associated with this verification could not be found.', 'danger')
                return redirect(url_for('auth.forgot_password'))
        else:
            flash(message, 'danger')

    can_resend, remaining_cooldown = EmailOTP.can_resend(email, 'password_reset', cooldown_seconds=60) if email else (True, 0)
    return render_template('auth/reset_password.html', 
                           form=form, 
                           email=email, 
                           can_resend=can_resend, 
                           cooldown=remaining_cooldown)
