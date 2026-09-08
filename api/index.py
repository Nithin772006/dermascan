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
    Handles:
      - PATH_INFO stripped of '/api' (e.g. '/signup' -> '/api/signup')
      - Vercel passing script name like '/api/index.py' -> recovers path from HTTP_X_MATCHED_PATH / HTTP_X_FORWARDED_URI
      - Empty or root -> '/api'
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        matched = environ.get("HTTP_X_MATCHED_PATH") or environ.get("HTTP_X_FORWARDED_URI")
        if path in ("", "/", "/api/index.py", "/api/index", "/index.py") and matched:
            path = matched.split("?")[0]

        if not path or path == "/":
            environ["PATH_INFO"] = "/api"
        elif not path.startswith("/api"):
            environ["PATH_INFO"] = "/api" + path
        else:
            environ["PATH_INFO"] = path
        return self.wsgi_app(environ, start_response)


# Wrap the Flask app with the WSGI path normalizer
app.wsgi_app = VercelPathMiddleware(app.wsgi_app)
