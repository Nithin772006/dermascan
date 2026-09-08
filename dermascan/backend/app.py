"""
app.py (v2)
Serves the DermaScan frontend and a small REST + session-auth API from
one Flask process — designed to run inside Colab behind an ngrok tunnel,
or locally.

Auth: simple session-cookie auth (Flask's built-in signed session,
werkzeug password hashing, SQLite for storage). This is fine for a
college project demo — it is NOT hardened for production use (no rate
limiting, no email verification, no HTTPS enforcement).

Endpoints:
  GET  /                      -> index.html
  POST /api/signup             {name, email, password}
  POST /api/login              {email, password}
  POST /api/logout
  GET  /api/me                 -> current session user, or 401
  POST /api/predict            multipart "image" (requires login) -> saves scan to history
  GET  /api/dashboard/stats    (requires login) -> totals, breakdown, recent scans
  POST /api/contact            {name, email, message}
  GET  /api/health
"""

import io
import os
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
import random

from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import numpy as np

import db
from model import CLASS_NAMES, IMG_SIZE
from utils import read_image_from_bytes, preprocess_image

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(BACKEND_DIR))
PUBLIC_DIR = os.path.join(ROOT_DIR, "public")
FRONTEND_DIR = PUBLIC_DIR if os.path.isdir(PUBLIC_DIR) else os.path.join(os.path.dirname(BACKEND_DIR), "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.secret_key = os.environ.get("DERMASCAN_SECRET_KEY", "dev-only-change-me-for-real-use")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
CORS(app, supports_credentials=True)

MODEL_PATH = os.path.join(BACKEND_DIR, "skin_model.h5")
MODEL_KERAS_PATH = os.path.join(BACKEND_DIR, "skin_model.keras")
_model = None
_using_mock = True


def load_model_if_available():
    global _model, _using_mock
    target_path = None
    if os.path.exists(MODEL_PATH):
        target_path = MODEL_PATH
    elif os.path.exists(MODEL_KERAS_PATH):
        target_path = MODEL_KERAS_PATH

    if target_path:
        try:
            import tensorflow as tf
            _model = tf.keras.models.load_model(target_path)
            _using_mock = False
            print(f"[DermaScan] Loaded trained model from {target_path}")
        except Exception as e:
            _using_mock = True
            print(f"[DermaScan] Model loading failed ({e}) — serving MOCK predictions.")
    else:
        _using_mock = True
        print("[DermaScan] No trained model found — serving MOCK predictions.")


# Initialize DB and model on module import (essential for Vercel Serverless WSGI)
try:
    db.init_db()
except Exception as _e:
    print(f"[DermaScan] DB initialization warning: {_e}")

try:
    load_model_if_available()
except Exception as _e:
    print(f"[DermaScan] Model initialization warning: {_e}")



def mock_predict(image_array: np.ndarray) -> np.ndarray:
    seed = int(np.sum(image_array)) % (2**32 - 1)
    rng = random.Random(seed)
    raw = [rng.uniform(0.05, 1.0) for _ in CLASS_NAMES]
    top_idx = raw.index(max(raw))
    raw[top_idx] *= 3.0
    total = sum(raw)
    return np.array([v / total for v in raw])


def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 401
        return fn(*args, **kwargs)
    return wrapper


# ---------- Frontend ----------
@app.route("/")
def home():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(FRONTEND_DIR, "index.html")
    return jsonify({
        "status": "online",
        "service": "DermaScan AI Backend",
        "frontend": "Served statically via Vercel Edge Network"
    })



# ---------- Auth ----------
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not (name and email and password):
        return jsonify({"error": "Name, email and password are all required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    user, error, status = db.signup_user(name, email, password)
    if error:
        return jsonify({"error": error}), status

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]
    return jsonify({"user": user})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not (email and password):
        return jsonify({"error": "Email and password are required"}), 400

    user, error, status = db.login_user(email, password)
    if error:
        return jsonify({"error": error}), status

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]
    return jsonify({"user": user})


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "logged_out"})


@app.route("/api/me", methods=["GET"])
def me():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    user = db.get_user_by_id(session["user_id"])
    if not user:
        if "user_name" in session and "user_email" in session:
            return jsonify({"user": {"id": session["user_id"], "name": session["user_name"], "email": session["user_email"]}})
        session.clear()
        return jsonify({"error": "Not logged in"}), 401
    return jsonify({"user": {"id": user.get("id"), "name": user.get("name"), "email": user.get("email")}})


# ---------- Prediction (protected) ----------
@app.route("/api/predict", methods=["POST"])
@login_required
def predict():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided under field 'image'"}), 400

    file = request.files["image"]
    try:
        img_array = read_image_from_bytes(io.BytesIO(file.read()))
    except Exception as e:
        return jsonify({"error": f"Could not read image: {e}"}), 400

    processed = preprocess_image(img_array)

    if _using_mock:
        probs = mock_predict(processed[0])
    else:
        preds = _model.predict(processed, verbose=0)
        probs = preds[0]

    top_idx = int(np.argmax(probs))
    prediction = CLASS_NAMES[top_idx]
    confidence = float(probs[top_idx])
    probabilities = {CLASS_NAMES[i]: float(probs[i]) for i in range(len(CLASS_NAMES))}

    db.create_scan(session["user_id"], prediction, confidence, probabilities)

    return jsonify({
        "prediction": prediction,
        "confidence": confidence,
        "probabilities": probabilities,
        "mode": "mock" if _using_mock else "trained_model",
    })


# ---------- Dashboard (protected) ----------
@app.route("/api/dashboard/stats", methods=["GET"])
@login_required
def dashboard_stats():
    stats = db.get_dashboard_stats(session["user_id"])
    return jsonify(stats)


# ---------- Contact (public) ----------
@app.route("/api/contact", methods=["POST"])
def contact():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    message = data.get("message", "").strip()
    if not (name and email and message):
        return jsonify({"error": "name, email and message are all required"}), 400
    print(f"[Contact] {name} <{email}>: {message}")
    return jsonify({"status": "received"})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "mode": "mock" if _using_mock else "trained_model",
        "database": "supabase" if db.is_supabase_enabled() else "sqlite",
    })


@app.route("/api", methods=["GET"])
@app.route("/api/", methods=["GET"])
def api_root():
    return jsonify({
        "name": "DermaScan AI API",
        "status": "online",
        "version": "2.0",
        "mode": "mock" if _using_mock else "trained_model",
        "database": "supabase" if db.is_supabase_enabled() else "sqlite",
        "endpoints": [
            "/api/signup",
            "/api/login",
            "/api/logout",
            "/api/me",
            "/api/predict",
            "/api/dashboard/stats",
            "/api/contact",
            "/api/health"
        ]
    })


if __name__ == "__main__":
    db.init_db()
    load_model_if_available()
    app.run(port=5000)

