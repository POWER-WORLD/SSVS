import os
import sys
import logging
from app import create_app

# Auto-detect production on Render vs development locally
env_name = os.environ.get('FLASK_ENV') or ('production' if os.environ.get('RENDER') else 'development')
print(f"Initializing SSVS with config: {env_name}...", flush=True)
app = create_app(env_name)
print("SSVS Application created successfully!", flush=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = (os.environ.get('FLASK_DEBUG', '0') == '1') and not os.environ.get('RENDER')
    print(f"Starting SSVS on http://127.0.0.1:{port}...", flush=True)
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)

