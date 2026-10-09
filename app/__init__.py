import os
from flask import Flask, render_template, request
from app.config import config
from app.models import db, login_manager, migrate, csrf
from app.auth import auth_bp
from app.dashboard import dashboard_bp
from app.forms_mgr import forms_mgr_bp
from app.student import student_bp
from app.analytics import analytics_bp
from app.api import api_bp

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV') or ('production' if os.environ.get('RENDER') else 'development')
    if config_name not in config:
        config_name = 'production' if os.environ.get('RENDER') else 'development'

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Apply ProxyFix only in production behind reverse proxies (Render / Heroku / Nginx)
    if config_name == 'production' or os.environ.get('RENDER'):
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

        try:
            from whitenoise import WhiteNoise
            static_dir = os.path.join(app.root_path, 'static')
            app.wsgi_app = WhiteNoise(app.wsgi_app, root=static_dir, prefix='static/')
        except ImportError:
            pass

    # Ensure required directories exist
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, '..', 'instance'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Exempt API blueprint from CSRF for asynchronous JSON requests if desired or allow header
    # We will pass CSRF token in JS headers, but for testing endpoints we exempt api_bp
    csrf.exempt(api_bp)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(forms_mgr_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(api_bp)

    # Performance: set client-side caching header for static assets
    @app.after_request
    def set_cache_headers(response):
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=86400'
        return response

    # Lightweight health check endpoint for Render/uptime monitoring
    @app.route('/healthz')
    def health_check():
        return {'status': 'healthy', 'service': 'SSVS'}, 200

    # Register template filters & context processors
    @app.context_processor
    def inject_globals():
        return {
            'app_name': 'Student Score View System',
            'app_short': 'SSVS',
            'current_year': 2026
        }

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    # Idempotent schema creation (run on explicit flag, in testing, or on Render deployment)
    if app.config.get('TESTING') or os.environ.get('INIT_DB') == '1' or os.environ.get('RENDER'):
        with app.app_context():
            try:
                db.create_all()
            except Exception as e:
                app.logger.warning(f"Schema init notice: {e}")

    return app

