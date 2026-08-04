import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent / "academic_audit.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db() -> None:
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS branches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS years (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            section TEXT NOT NULL,
            branch TEXT NOT NULL,
            year TEXT NOT NULL,
            subject TEXT NOT NULL,
            marks_obtained REAL NOT NULL,
            max_marks REAL NOT NULL,
            entered_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            action TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            details TEXT NOT NULL
        );
        """
    )
    conn.commit()
    seed_defaults(conn)
    conn.close()


def seed_defaults(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)", ("registrar", hash_password("registrar123"), "registrar"))
    conn.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)", ("admin", hash_password("admin123"), "admin"))
    for name in ["A", "B", "C"]:
        conn.execute("INSERT OR IGNORE INTO sections (name) VALUES (?)", (name,))
    for name in ["CSE", "ECE", "ME"]:
        conn.execute("INSERT OR IGNORE INTO branches (name) VALUES (?)", (name,))
    for name in ["1st", "2nd", "3rd", "4th"]:
        conn.execute("INSERT OR IGNORE INTO years (name) VALUES (?)", (name,))
    for name in ["Data Structures", "Mathematics", "Physics", "English"]:
        conn.execute("INSERT OR IGNORE INTO subjects (name) VALUES (?)", (name,))
    conn.commit()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    user = conn.execute("SELECT id, username, role FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if not user:
        return None
    if verify_password(password, get_user_password_hash(username)):
        return {"id": user["id"], "username": user["username"], "role": user["role"]}
    return None


def get_user_password_hash(username: str) -> str:
    conn = get_connection()
    row = conn.execute("SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row["password_hash"] if row else ""


def username_exists(username: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row is not None


def create_user(username: str, password_hash: str, role: str) -> None:
    conn = get_connection()
    conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", (username, password_hash, role))
    conn.commit()
    conn.close()


def get_options(table_name: str) -> List[str]:
    allowed = {"sections", "branches", "years", "subjects"}
    if table_name not in allowed:
        raise ValueError("Unsupported option table")
    conn = get_connection()
    rows = conn.execute(f"SELECT name FROM {table_name} ORDER BY name").fetchall()
    conn.close()
    return [row["name"] for row in rows]


def add_option(table_name: str, name: str) -> None:
    allowed = {"sections", "branches", "years", "subjects"}
    if table_name not in allowed:
        raise ValueError("Unsupported option table")
    if not name or not name.strip():
        return
    conn = get_connection()
    conn.execute(f"INSERT OR IGNORE INTO {table_name} (name) VALUES (?)", (name.strip(),))
    conn.commit()
    conn.close()


def insert_record(student_name: str, section: str, branch: str, year: str, subject: str, marks_obtained: float, max_marks: float, entered_by: str) -> int:
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO records (student_name, section, branch, year, subject, marks_obtained, max_marks, entered_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (student_name, section, branch, year, subject, marks_obtained, max_marks, entered_by, now, now),
    )
    conn.commit()
    conn.close()
    return cursor.lastrowid


def update_record(record_id: int, student_name: str, section: str, branch: str, year: str, subject: str, marks_obtained: float, max_marks: float) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE records SET student_name = ?, section = ?, branch = ?, year = ?, subject = ?, marks_obtained = ?, max_marks = ?, updated_at = ? WHERE id = ?",
        (student_name, section, branch, year, subject, marks_obtained, max_marks, datetime.utcnow().isoformat(), record_id),
    )
    conn.commit()
    conn.close()


def get_all_records(filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    query = "SELECT id, student_name, section, branch, year, subject, marks_obtained, max_marks, entered_by, created_at, updated_at FROM records"
    clauses: List[str] = []
    params: List[Any] = []
    if filters:
        for field in ["student_name", "section", "branch", "year", "subject"]:
            value = filters.get(field)
            if value not in (None, "", "All"):
                clauses.append(f"{field} = ?")
                params.append(value)
    if clauses:
        query = f"{query} WHERE {' AND '.join(clauses)}"
    query = f"{query} ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_record(record_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def add_audit_log(user_id: int, action: str, details: Dict[str, Any]) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO audit_log (user_id, action, timestamp, details) VALUES (?, ?, ?, ?)",
        (user_id, action, datetime.utcnow().isoformat(), str(details)),
    )
    conn.commit()
    conn.close()


def get_recent_activity(limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT a.id, a.action, a.timestamp, a.details, u.username FROM audit_log a JOIN users u ON u.id = a.user_id ORDER BY a.id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
