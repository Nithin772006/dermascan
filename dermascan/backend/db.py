"""
db.py
Tiny SQLite layer for users + scan history. No ORM — plain sqlite3,
kept intentionally simple for a college project.
"""

import os
import sqlite3
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dermascan.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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
    print(f"[DermaScan] Database ready at {DB_PATH}")


def create_user(name: str, email: str, password_hash: str):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (name, email, password_hash, datetime.utcnow().isoformat()),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def get_user_by_email(email: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_scan(user_id: int, prediction: str, confidence: float, probabilities: dict):
    conn = get_conn()
    conn.execute(
        "INSERT INTO scans (user_id, prediction, confidence, probabilities, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, prediction, confidence, json.dumps(probabilities), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_dashboard_stats(user_id: int):
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
