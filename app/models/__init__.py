from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'
migrate = Migrate()
csrf = CSRFProtect()

from .user import Teacher
from .form import Form, FormField, FieldOption
from .submission import Submission, SubmissionValue
from .platform_profile import PlatformProfile
from .scoring import ScoreFormula, FormulaRule, CalculatedScore, LeaderboardEntry
from .audit import ActivityLog
from .otp import EmailOTP

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Teacher, int(user_id))
