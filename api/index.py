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


from urllib.parse import parse_qs, urlencode


class VercelPathMiddleware:
    """
    Normalizes incoming WSGI request paths for Vercel Serverless Function deployments.
    Extracts the real intended route from:
      1. Query parameter '__route__' (injected by vercel.json rewrite)
      2. Headers: HTTP_X_FORWARDED_URI, HTTP_X_MATCHED_PATH
      3. Normalizes empty or root to '/api'
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        query_string = environ.get("QUERY_STRING", "")
        target_path = None

        # 1. Check for __route__ injected by vercel.json rewrite rule
        if "__route__=" in query_string:
            params = parse_qs(query_string, keep_blank_values=True)
            if "__route__" in params and params["__route__"]:
                target_path = params.pop("__route__")[0]
                # Reconstruct clean QUERY_STRING without the internal __route__ param
                clean_pairs = []
                for k, vs in params.items():
                    for v in vs:
                        clean_pairs.append((k, v))
                environ["QUERY_STRING"] = urlencode(clean_pairs)

        # 2. If no __route__ found, inspect headers and PATH_INFO
        if not target_path:
            path_info = environ.get("PATH_INFO", "")
            matched = environ.get("HTTP_X_FORWARDED_URI") or environ.get("HTTP_X_MATCHED_PATH")
            if path_info in ("", "/", "/api/index.py", "/api/index", "/index.py") and matched:
                target_path = matched.split("?")[0]
            else:
                target_path = path_info

        # 3. Ensure path is prefixed with /api
        if not target_path or target_path == "/":
            target_path = "/api"
        elif not target_path.startswith("/api"):
            target_path = "/api" + target_path

        environ["PATH_INFO"] = target_path
        return self.wsgi_app(environ, start_response)


# Wrap the Flask app with the WSGI path normalizer
app.wsgi_app = VercelPathMiddleware(app.wsgi_app)
