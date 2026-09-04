from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db
from app.models.user import Teacher
from app.models.audit import ActivityLog
from app.auth.forms import LoginForm, RegistrationForm, ForgotPasswordForm, ProfileForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.overview'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = Teacher.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'danger')
                return render_template('auth/login.html', form=form)
                
            login_user(user, remember=form.remember.data)
            
            # Audit log
            db.session.add(ActivityLog(
                teacher_id=user.id,
                action='LOGIN',
                description=f'Logged in from {request.remote_addr}',
                ip_address=request.remote_addr
            ))
            db.session.commit()
            
            flash(f'Welcome back, Prof. {user.full_name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.overview'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
            
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.overview'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        user = Teacher(
            email=form.email.data.lower().strip(),
            full_name=form.full_name.data.strip(),
            college_name=form.college_name.data.strip(),
            department=form.department.data.strip(),
            designation=form.designation.data.strip(),
            phone=form.phone.data.strip() if form.phone.data else None
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        
        db.session.add(ActivityLog(
            teacher_id=user.id,
            action='REGISTER',
            description='Created teacher account',
            ip_address=request.remote_addr
        ))
        db.session.commit()
        
        flash('Account created successfully! Welcome to SSVS.', 'success')
        return redirect(url_for('dashboard.overview'))
        
    return render_template('auth/register.html', form=form)

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
        
    logs = current_user.activity_logs.order_by(ActivityLog.created_at.desc()).limit(10).all()
    return render_template('auth/profile.html', form=form, logs=logs)

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        # Demo simulation for forgot password
        flash('If an account matches that email, password reset instructions have been generated.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html', form=form)
