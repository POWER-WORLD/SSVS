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

    # Performance & Security Headers
    @app.after_request
    def set_cache_and_security_headers(response):
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=86400'
        
        # Apply configured enterprise security headers
        sec_headers = app.config.get('SECURITY_HEADERS', {})
        for header, value in sec_headers.items():
            if header not in response.headers:
                response.headers[header] = value

        # Dynamic CORS headers matching allowed origins
        origin = request.headers.get('Origin')
        allowed_origins = app.config.get('CORS_ORIGINS', [])
        if origin and (origin in allowed_origins or '*' in allowed_origins):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true' if app.config.get('CORS_ALLOW_CREDENTIALS', True) else 'false'
            response.headers['Access-Control-Allow-Methods'] = ', '.join(app.config.get('CORS_ALLOW_METHODS', ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']))
            response.headers['Access-Control-Allow-Headers'] = ', '.join(app.config.get('CORS_ALLOW_HEADERS', ['Content-Type', 'Authorization', 'X-Requested-With', 'X-CSRFToken', 'Accept']))
            response.headers['Access-Control-Max-Age'] = str(app.config.get('CORS_MAX_AGE', 86400))
        elif not origin and allowed_origins:
            # Default fallback header for direct requests
            response.headers['Access-Control-Allow-Origin'] = allowed_origins[0]

        return response

    # Handle CORS preflight for all routes
    @app.before_request
    def handle_cors_preflight():
        if request.method == 'OPTIONS':
            origin = request.headers.get('Origin')
            allowed_origins = app.config.get('CORS_ORIGINS', [])
            if origin and (origin in allowed_origins or '*' in allowed_origins):
                from flask import Response
                res = Response(status=204)
                res.headers['Access-Control-Allow-Origin'] = origin
                res.headers['Access-Control-Allow-Credentials'] = 'true' if app.config.get('CORS_ALLOW_CREDENTIALS', True) else 'false'
                res.headers['Access-Control-Allow-Methods'] = ', '.join(app.config.get('CORS_ALLOW_METHODS', ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']))
                res.headers['Access-Control-Allow-Headers'] = ', '.join(app.config.get('CORS_ALLOW_HEADERS', ['Content-Type', 'Authorization', 'X-Requested-With', 'X-CSRFToken', 'Accept']))
                res.headers['Access-Control-Max-Age'] = str(app.config.get('CORS_MAX_AGE', 86400))
                return res

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
        if request.path.startswith('/api/') or (request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html):
            return {'error': 'Not Found', 'message': 'The requested resource was not found.', 'status_code': 404}, 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.path.startswith('/api/') or (request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html):
            return {'error': 'Internal Server Error', 'message': 'An unexpected server error occurred.', 'status_code': 500}, 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        if request.path.startswith('/api/') or (request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html):
            return {'error': 'Forbidden', 'message': 'Access to this resource is denied.', 'status_code': 403}, 403
        return render_template('errors/403.html'), 403

    # Idempotent schema creation (run on explicit flag, in testing, or on Render deployment)
    if app.config.get('TESTING') or os.environ.get('INIT_DB') == '1' or os.environ.get('RENDER'):
        with app.app_context():
            try:
                db.create_all()
            except Exception as e:
                app.logger.warning(f"Schema init notice: {e}")

    return app

