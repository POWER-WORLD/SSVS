from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models.user import Teacher

class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    college_name = StringField('College / University Name', validators=[DataRequired(), Length(min=3, max=200)])
    department = StringField('Department', validators=[DataRequired(), Length(min=2, max=100)])
    designation = StringField('Designation', validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField('Contact Phone', validators=[Length(max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, message="Password must be at least 6 characters")])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message="Passwords must match")])
    submit = SubmitField('Create Teacher Account')

    def validate_email(self, email):
        user = Teacher.query.filter_by(email=email.data.lower().strip()).first()
        if user:
            raise ValidationError('An account with this email address already exists.')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Registered Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Password Reset Instructions')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Update Password')

class ProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    college_name = StringField('College / University Name', validators=[DataRequired(), Length(max=200)])
    department = StringField('Department', validators=[DataRequired(), Length(max=100)])
    designation = StringField('Designation', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Contact Phone', validators=[Length(max=20)])
    submit = SubmitField('Save Profile Changes')
