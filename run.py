import os
import logging
from app import create_app
from app.models import db

# Auto-detect production on Render vs development locally
env_name = os.environ.get('FLASK_ENV') or ('production' if os.environ.get('RENDER') else 'development')
app = create_app(env_name)

# Ensure database tables exist
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        app.logger.warning("Auto db.create_all encountered an issue: %s", e)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = (os.environ.get('FLASK_DEBUG', '0') == '1') and not os.environ.get('RENDER')
    app.run(host='0.0.0.0', port=port, debug=debug)

