"""
api/index.py — Vercel Serverless Function Entry Point for DermaScan AI.
"""

import os
import sys

# Ensure backend directory and project root are on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT_DIR, "dermascan", "backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app


class VercelPathMiddleware:
    """
    Normalizes incoming WSGI request paths.
    If Vercel rewrites /api/(.*) and forwards the path stripped of '/api',
    this middleware prepends '/api' so Flask routes like @app.route('/api/login')
    match correctly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if not path or path == "/":
            environ["PATH_INFO"] = "/api"
        elif not path.startswith("/api"):
            environ["PATH_INFO"] = "/api" + path
        return self.wsgi_app(environ, start_response)


# Wrap the Flask app with the WSGI path normalizer
app.wsgi_app = VercelPathMiddleware(app.wsgi_app)
