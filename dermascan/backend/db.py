"""
db.py
Dual-Engine Data & Authentication Layer for DermaScan AI.
Supports:
  1. Supabase (PostgreSQL + Supabase Auth) when SUPABASE_URL and SUPABASE_KEY are configured.
  2. Local/Serverless SQLite (dermascan.db or /tmp/dermascan.db) as a seamless fallback.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, Union
from werkzeug.security import generate_password_hash, check_password_hash

# Try importing supabase
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

_supabase_client: Optional[Any] = None


def load_env_file():
    """Lightweight zero-dependency .env reader for local development."""
    search_paths = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
    ]
    for path in search_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
                break
            except Exception:
                pass


# Pre-load .env if available
load_env_file()


# ==============================================================================
# 1. Supabase Client & Detection
# ==============================================================================

def get_supabase_client() -> Optional[Any]:
    """
    Initializes and returns the Supabase client if SUPABASE_URL and SUPABASE_KEY are set.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    load_env_file()
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
    )

    if supabase_url and supabase_key and create_client is not None:
        try:
            _supabase_client = create_client(supabase_url, supabase_key)
            print(f"[DermaScan] Initialized Supabase client for {supabase_url}")
        except Exception as e:
            print(f"[DermaScan] Warning: Could not connect to Supabase: {e}")
            _supabase_client = None

    return _supabase_client


def is_supabase_enabled() -> bool:
    """Returns True if Supabase client is configured and available."""
    return get_supabase_client() is not None


# ==============================================================================
# 2. SQLite Database Engine (Local / Offline / Fallback)
# ==============================================================================

def get_db_path() -> str:
    """
    Returns the SQLite database file path.
    If running on Vercel / AWS Lambda (where the source filesystem is strictly read-only),
    we store or copy the database to /tmp to allow write operations.
    """
    if "DB_PATH" in os.environ:
        return os.environ["DB_PATH"]

    is_serverless = bool(
        os.environ.get("VERCEL")
        or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
        or os.environ.get("LAMBDA_TASK_ROOT")
    )

    local_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dermascan.db")

    if is_serverless:
        import tempfile
        tmp_dir = "/tmp" if os.path.isdir("/tmp") or os.name != "nt" else tempfile.gettempdir()
        tmp_db = os.path.join(tmp_dir, "dermascan.db")
        if not os.path.exists(tmp_db) and os.path.exists(local_db):
            try:
                import shutil
                shutil.copy2(local_db, tmp_db)
            except Exception as e:
                print(f"[DermaScan DB] Warning: could not seed tmp DB from repo: {e}")
        return tmp_db

    return local_db


def get_conn():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite_db():
    db_path = get_db_path()
    parent = os.path.dirname(db_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prediction TEXT NOT NULL,
            confidence REAL NOT NULL,
            probabilities TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()
    print(f"[DermaScan] SQLite database ready at {db_path}")


def init_db():
    """Initializes the database layer (Supabase if configured, otherwise SQLite)."""
    if is_supabase_enabled():
        print("[DermaScan] Using Supabase cloud database & authentication.")
    else:
        init_sqlite_db()


# ==============================================================================
# 3. Supabase Operations
# ==============================================================================

def supabase_signup(name: str, email: str, password: str) -> Tuple[Optional[Dict], Optional[str], int]:
    sb = get_supabase_client()
    try:
        res = sb.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"name": name}}
        })
        if not res.user:
            return None, "Supabase signup failed", 400

        user_id = str(res.user.id)
        user_email = res.user.email or email

        # Ensure profile exists in public.profiles table
        try:
            sb.table("profiles").upsert({
                "id": user_id,
                "name": name,
                "email": user_email
            }).execute()
        except Exception as _e:
            pass  # Trigger or RLS may handle it

        return {"id": user_id, "name": name, "email": user_email}, None, 200
    except Exception as e:
        err_msg = str(e)
        if "already registered" in err_msg.lower() or "unique constraint" in err_msg.lower():
            return None, "An account with that email already exists", 409
        return None, err_msg, 400


def supabase_login(email: str, password: str) -> Tuple[Optional[Dict], Optional[str], int]:
    sb = get_supabase_client()
    try:
        res = sb.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if not res.user:
            return None, "Invalid email or password", 401

        user_id = str(res.user.id)
        user_email = res.user.email or email

        # Retrieve profile name
        name = ""
        if res.user.user_metadata and "name" in res.user.user_metadata:
            name = res.user.user_metadata["name"]
        if not name:
            try:
                p_res = sb.table("profiles").select("name").eq("id", user_id).limit(1).execute()
                if p_res.data and len(p_res.data) > 0:
                    name = p_res.data[0].get("name", "")
            except Exception:
                pass
        if not name:
            name = user_email.split("@")[0]

        return {"id": user_id, "name": name, "email": user_email}, None, 200
    except Exception as e:
        err_msg = str(e)
        if "invalid login credentials" in err_msg.lower() or "invalid credentials" in err_msg.lower():
            return None, "Invalid email or password", 401
        return None, err_msg, 401


def supabase_get_user(user_id: str) -> Optional[Dict]:
    sb = get_supabase_client()
    try:
        p_res = sb.table("profiles").select("*").eq("id", str(user_id)).limit(1).execute()
        if p_res.data and len(p_res.data) > 0:
            return p_res.data[0]
    except Exception:
        pass
    return None


def supabase_create_scan(user_id: str, prediction: str, confidence: float, probabilities: dict):
    sb = get_supabase_client()
    try:
        sb.table("scans").insert({
            "user_id": str(user_id),
            "prediction": prediction,
            "confidence": float(confidence),
            "probabilities": probabilities
        }).execute()
    except Exception as e:
        print(f"[DermaScan Supabase] Error inserting scan: {e}")


def supabase_get_dashboard_stats(user_id: str) -> Dict:
    sb = get_supabase_client()
    try:
        res = sb.table("scans").select("prediction, confidence, created_at").eq("user_id", str(user_id)).order("created_at", desc=True).execute()
        rows = res.data or []
    except Exception as e:
        print(f"[DermaScan Supabase] Error fetching stats: {e}")
        rows = []

    total = len(rows)
    try:
        from model import CLASS_NAMES
        condition_counts = {c: 0 for c in CLASS_NAMES}
    except Exception:
        condition_counts = {}

    melanoma_flags = 0
    for r in rows:
        pred = r.get("prediction", "")
        condition_counts[pred] = condition_counts.get(pred, 0) + 1
        if "melanoma" in pred.lower():
            melanoma_flags += 1

    most_common = max(condition_counts, key=condition_counts.get) if total else None
    avg_confidence = sum(r.get("confidence", 0) for r in rows) / total if total else 0

    return {
        "total_scans": total,
        "condition_counts": condition_counts,
        "most_common": most_common,
        "avg_confidence": avg_confidence,
        "melanoma_flags": melanoma_flags,
        "recent": rows[:8],
    }


# ==============================================================================
# 4. Unified Interface (Used by app.py)
# ==============================================================================

def signup_user(name: str, email: str, password: str) -> Tuple[Optional[Dict], Optional[str], int]:
    """
    Unified user registration.
    Uses Supabase Auth if enabled, otherwise SQLite.
    Returns: (user_dict, error_message, status_code)
    """
    if is_supabase_enabled():
        return supabase_signup(name, email, password)

    # SQLite Fallback
    if get_user_by_email(email):
        return None, "An account with that email already exists", 409

    pwd_hash = generate_password_hash(password)
    user_id = create_sqlite_user(name, email, pwd_hash)
    return {"id": user_id, "name": name, "email": email}, None, 200


def login_user(email: str, password: str) -> Tuple[Optional[Dict], Optional[str], int]:
    """
    Unified user login.
    Uses Supabase Auth if enabled, otherwise SQLite password verification.
    Returns: (user_dict, error_message, status_code)
    """
    if is_supabase_enabled():
        return supabase_login(email, password)

    # SQLite Fallback
    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return None, "Invalid email or password", 401

    return {"id": user["id"], "name": user["name"], "email": user["email"]}, None, 200


def get_user_by_id(user_id: Union[int, str]) -> Optional[Dict]:
    """Retrieves user profile by ID (UUID string for Supabase or int for SQLite)."""
    if is_supabase_enabled():
        return supabase_get_user(str(user_id))

    # SQLite
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_scan(user_id: Union[int, str], prediction: str, confidence: float, probabilities: dict):
    """Saves scan prediction into Supabase 'scans' table or SQLite 'scans' table."""
    if is_supabase_enabled():
        return supabase_create_scan(str(user_id), prediction, confidence, probabilities)

    # SQLite
    conn = get_conn()
    conn.execute(
        "INSERT INTO scans (user_id, prediction, confidence, probabilities, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, prediction, confidence, json.dumps(probabilities), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_dashboard_stats(user_id: Union[int, str]) -> Dict:
    """Retrieves aggregated statistics and scan history for the user."""
    if is_supabase_enabled():
        return supabase_get_dashboard_stats(str(user_id))

    # SQLite
    conn = get_conn()
    rows = conn.execute(
        "SELECT prediction, confidence, created_at FROM scans WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()

    rows = [dict(r) for r in rows]
    total = len(rows)

    try:
        from model import CLASS_NAMES
        condition_counts = {c: 0 for c in CLASS_NAMES}
    except Exception:
        condition_counts = {}

    melanoma_flags = 0
    for r in rows:
        pred = r["prediction"]
        condition_counts[pred] = condition_counts.get(pred, 0) + 1
        if "melanoma" in pred.lower():
            melanoma_flags += 1

    most_common = max(condition_counts, key=condition_counts.get) if total else None
    avg_confidence = sum(r["confidence"] for r in rows) / total if total else 0

    return {
        "total_scans": total,
        "condition_counts": condition_counts,
        "most_common": most_common,
        "avg_confidence": avg_confidence,
        "melanoma_flags": melanoma_flags,
        "recent": rows[:8],
    }


# ==============================================================================
# 5. SQLite Legacy Helpers (Maintained for complete backward compatibility)
# ==============================================================================

def create_sqlite_user(name: str, email: str, password_hash: str) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (name, email, password_hash, datetime.utcnow().isoformat()),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def create_user(name: str, email: str, password_hash: str) -> int:
    return create_sqlite_user(name, email, password_hash)


def get_user_by_email(email: str) -> Optional[Dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None
