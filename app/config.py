import os
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

def get_database_uri(default_sqlite_name='ssvs_dev.db'):
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        # Adapt driver dialect if specific driver is missing in environment
        if db_url.startswith('postgresql://'):
            try:
                import socket
                from urllib.parse import urlparse
                parsed = urlparse(db_url)
                if parsed.hostname:
                    socket.setdefaulttimeout(2.0)
                    socket.gethostbyname(parsed.hostname)
            except Exception:
                # Fallback to local SQLite when remote host is unreachable/offline
                return f"sqlite:///{os.path.join(BASE_DIR, 'instance', default_sqlite_name)}"

            try:
                import psycopg  # psycopg v3 is preferred
            except ImportError:
                try:
                    import psycopg2
                    db_url = db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
                except ImportError:
                    pass
        return db_url
    return f"sqlite:///{os.path.join(BASE_DIR, 'instance', default_sqlite_name)}"

def mask_db_url(url: str) -> str:
    """Masks database password in connection string for safe logging and display."""
    if not url or '@' not in url:
        return url
    import re
    return re.sub(r':([^:@]+)@', ':***@', url)


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ssvs-super-secret-enterprise-key-2026-secure')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
    }
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'csv', 'xlsx'}
    
    # Session security
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Platform extraction settings
    EXTRACTION_TIMEOUT = 12  # seconds per platform request
    MOCK_ON_RATE_LIMIT = True
    
    # QR Code storage
    QR_FOLDER = os.path.join(BASE_DIR, 'uploads', 'qrcodes')

    # Cross-Origin Resource Sharing (CORS) settings
    _cors_env = os.environ.get('CORS_ORIGINS', '')
    CORS_ORIGINS = [
        origin.strip()
        for origin in (_cors_env.split(',') if _cors_env else [
            'https://ssvsportal.onrender.com',
            'https://skgmobile.netlify.app',
            'http://localhost:3000',
            'http://localhost:5173',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:5173'
        ])
        if origin.strip()
    ]
    if 'https://ssvsportal.onrender.com' not in CORS_ORIGINS:
        CORS_ORIGINS.append('https://ssvsportal.onrender.com')
    if 'https://skgmobile.netlify.app' not in CORS_ORIGINS:
        CORS_ORIGINS.append('https://skgmobile.netlify.app')

    CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'X-Requested-With', 'X-CSRFToken', 'Accept']
    CORS_ALLOW_CREDENTIALS = True
    CORS_MAX_AGE = 86400

    # Enterprise Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=(), payment=()',
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' data: https://cdn.jsdelivr.net https://fonts.gstatic.com; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https://ssvsportal.onrender.com https://skgmobile.netlify.app; "
            "frame-ancestors 'self';"
        )
    }

    # Google Apps Script Email Gateway Settings
    GAS_EMAIL_URL = os.environ.get('GAS_EMAIL_URL', '')
    GAS_SECRET_TOKEN = os.environ.get('GAS_SECRET_TOKEN', '')
    GAS_REQUEST_TIMEOUT = int(os.environ.get('GAS_REQUEST_TIMEOUT', 15))

    @classmethod
    def get_engine_options(cls, uri: str) -> dict:
        if uri and 'sqlite' in uri:
            return {}
        return {
            'pool_pre_ping': True,
            'pool_recycle': 280,
            'pool_size': 10,
            'max_overflow': 20,
            'pool_timeout': 30,
        }

    @classmethod
    def init_app(cls, app):
        pass

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = get_database_uri('ssvs_dev.db')
    SQLALCHEMY_ENGINE_OPTIONS = Config.get_engine_options(get_database_uri('ssvs_dev.db'))
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Content-Security-Policy': (
            "default-src 'self' https: data: blob: 'unsafe-inline' 'unsafe-eval'; "
            "font-src 'self' data: https:; "
            "img-src 'self' data: https: blob:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https:;"
        )
    }

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    GAS_EMAIL_URL = 'https://script.google.com/macros/s/test-deployment-id/exec'
    GAS_SECRET_TOKEN = 'test_gas_secret_token_2026'

class ProductionConfig(Config):
    """Production configuration with enterprise hardening."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = get_database_uri('ssvs_prod.db')
    
    # Enforce HTTPS and secure cookie policies
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    PREFERRED_URL_SCHEME = 'https'

    # HSTS in production
    HSTS_ENABLED = True
    HSTS_MAX_AGE = 31536000  # 1 year
    HSTS_INCLUDE_SUBDOMAINS = True
    HSTS_PRELOAD = True

    # Ensure CORS origins include ssvsportal.onrender.com and netlify in production
    _prod_cors_env = os.environ.get('CORS_ORIGINS', '')
    if _prod_cors_env:
        CORS_ORIGINS = [o.strip() for o in _prod_cors_env.split(',') if o.strip()]
        if 'https://ssvsportal.onrender.com' not in CORS_ORIGINS:
            CORS_ORIGINS.append('https://ssvsportal.onrender.com')
        if 'https://skgmobile.netlify.app' not in CORS_ORIGINS:
            CORS_ORIGINS.append('https://skgmobile.netlify.app')
    else:
        CORS_ORIGINS = ['https://ssvsportal.onrender.com', 'https://skgmobile.netlify.app']

    # Production database pool tuning
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 15)),
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 25)),
        'pool_timeout': 30,
    }

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        if not os.environ.get('SECRET_KEY'):
            app.logger.warning("Production SECRET_KEY environment variable not set! Set SECRET_KEY in the Render dashboard.")
        # Ensure security headers include HSTS in production
        if getattr(cls, 'HSTS_ENABLED', True):
            cls.SECURITY_HEADERS['Strict-Transport-Security'] = (
                f"max-age={cls.HSTS_MAX_AGE}; includeSubDomains; preload"
            )

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
