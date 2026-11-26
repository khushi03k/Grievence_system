"""SQLite storage: schema, complaint operations, admin users and dashboard queries."""
import hashlib
import hmac
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import pandas as pd

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL UNIQUE,
    severity REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS complaints (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_code      TEXT NOT NULL UNIQUE,
    text                TEXT NOT NULL,
    area                TEXT NOT NULL,
    contact             TEXT,
    category_id         INTEGER NOT NULL REFERENCES categories(id),
    priority_score      REAL NOT NULL,
    priority_label      TEXT NOT NULL CHECK (priority_label IN ('Low','Medium','High','Critical')),
    priority_overridden INTEGER NOT NULL DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'Open'
                        CHECK (status IN ('Open','In Progress','Resolved')),
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    resolved_at         TEXT
);

CREATE TABLE IF NOT EXISTS status_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES complaints(id),
    old_status   TEXT,
    new_status   TEXT NOT NULL,
    changed_by   TEXT NOT NULL,
    changed_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS override_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES complaints(id),
    field        TEXT NOT NULL CHECK (field IN ('category','priority')),
    old_value    TEXT NOT NULL,
    new_value    TEXT NOT NULL,
    changed_by   TEXT NOT NULL,
    changed_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_complaints_created  ON complaints(created_at);
CREATE INDEX IF NOT EXISTS idx_complaints_category ON complaints(category_id);
CREATE INDEX IF NOT EXISTS idx_complaints_priority ON complaints(priority_label);
CREATE INDEX IF NOT EXISTS idx_complaints_status   ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_area     ON complaints(area);
CREATE INDEX IF NOT EXISTS idx_history_complaint   ON status_history(complaint_id);
"""

COMPLAINT_SELECT = """
SELECT c.id, c.complaint_code, c.text, c.area, c.contact, cat.name AS category,
       c.priority_score, c.priority_label, c.priority_overridden, c.status,
       c.created_at, c.updated_at, c.resolved_at
FROM complaints c JOIN categories cat ON cat.id = c.category_id
"""


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def get_conn():
    """Open a connection, commit on success and always close it."""
    config.DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the tables and indexes and load the category list (safe to re-run)."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO categories (name, severity) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET severity = excluded.severity",
            list(config.CATEGORY_SEVERITY.items()),
        )


def category_ids(conn) -> dict:
    return {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM categories")}


def new_complaint_code() -> str:
    return "GRV-" + secrets.token_hex(4).upper()


# ------------------------------------------------------------- complaints ---
def insert_complaint(text, area, contact, category, priority_score, priority_label) -> str:
    """Store one complaint and return its unique complaint ID."""
    ts = now()
    with get_conn() as conn:
        cat_id = category_ids(conn)[category]
        while True:
            code = new_complaint_code()
            try:
                cur = conn.execute(
                    "INSERT INTO complaints (complaint_code, text, area, contact, category_id, "
                    "priority_score, priority_label, status, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 'Open', ?, ?)",
                    (code, text, area, contact or None, cat_id, priority_score, priority_label, ts, ts),
                )
                break
            except sqlite3.IntegrityError:  # extremely unlikely ID clash: try another ID
                continue
        conn.execute(
            "INSERT INTO status_history (complaint_id, old_status, new_status, changed_by, changed_at) "
            "VALUES (?, NULL, 'Open', 'citizen', ?)",
            (cur.lastrowid, ts),
        )
    return code


def get_complaint(code: str):
    with get_conn() as conn:
        row = conn.execute(COMPLAINT_SELECT + " WHERE c.complaint_code = ?", (code.strip().upper(),)).fetchone()
    return dict(row) if row else None


def get_status_history(code: str) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT h.changed_at, h.old_status, h.new_status, h.changed_by "
            "FROM status_history h JOIN complaints c ON c.id = h.complaint_id "
            "WHERE c.complaint_code = ? ORDER BY h.id",
            conn, params=(code,),
        )


def get_override_log(code: str) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT o.changed_at, o.field, o.old_value, o.new_value, o.changed_by "
            "FROM override_log o JOIN complaints c ON c.id = o.complaint_id "
            "WHERE c.complaint_code = ? ORDER BY o.id",
            conn, params=(code,),
        )


def update_status(code: str, new_status: str, admin: str) -> None:
    ts = now()
    with get_conn() as conn:
        row = conn.execute("SELECT id, status FROM complaints WHERE complaint_code = ?", (code,)).fetchone()
        if row is None or row["status"] == new_status:
            return
        resolved_at = ts if new_status == "Resolved" else None
        conn.execute(
            "UPDATE complaints SET status = ?, updated_at = ?, resolved_at = ? WHERE id = ?",
            (new_status, ts, resolved_at, row["id"]),
        )
        conn.execute(
            "INSERT INTO status_history (complaint_id, old_status, new_status, changed_by, changed_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (row["id"], row["status"], new_status, admin, ts),
        )


def override_category(code: str, new_category: str, admin: str) -> None:
    ts = now()
    with get_conn() as conn:
        row = conn.execute(COMPLAINT_SELECT + " WHERE c.complaint_code = ?", (code,)).fetchone()
        if row is None or row["category"] == new_category:
            return
        conn.execute(
            "UPDATE complaints SET category_id = ?, updated_at = ? WHERE id = ?",
            (category_ids(conn)[new_category], ts, row["id"]),
        )
        conn.execute(
            "INSERT INTO override_log (complaint_id, field, old_value, new_value, changed_by, changed_at) "
            "VALUES (?, 'category', ?, ?, ?, ?)",
            (row["id"], row["category"], new_category, admin, ts),
        )


def override_priority(code: str, new_label: str, admin: str) -> None:
    ts = now()
    with get_conn() as conn:
        row = conn.execute("SELECT id, priority_label FROM complaints WHERE complaint_code = ?", (code,)).fetchone()
        if row is None or row["priority_label"] == new_label:
            return
        conn.execute(
            "UPDATE complaints SET priority_label = ?, priority_overridden = 1, updated_at = ? WHERE id = ?",
            (new_label, ts, row["id"]),
        )
        conn.execute(
            "INSERT INTO override_log (complaint_id, field, old_value, new_value, changed_by, changed_at) "
            "VALUES (?, 'priority', ?, ?, ?, ?)",
            (row["id"], row["priority_label"], new_label, admin, ts),
        )


def set_priority(code: str, score: float, label: str) -> None:
    """Store a rule-based priority (not used for manual overrides)."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE complaints SET priority_score = ?, priority_label = ? WHERE complaint_code = ?",
            (score, label, code),
        )


def fetch_complaints(status=None, category=None, priority=None, area=None, search=None) -> pd.DataFrame:
    """Priority-sorted queue with optional filters (used by the admin console)."""
    where, params = [], []
    if status:
        where.append("c.status = ?"); params.append(status)
    if category:
        where.append("cat.name = ?"); params.append(category)
    if priority:
        where.append("c.priority_label = ?"); params.append(priority)
    if area:
        where.append("c.area = ?"); params.append(area)
    if search:
        where.append("(c.text LIKE ? OR c.complaint_code LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]
    sql = COMPLAINT_SELECT + (" WHERE " + " AND ".join(where) if where else "")
    sql += (" ORDER BY CASE c.priority_label WHEN 'Critical' THEN 4 WHEN 'High' THEN 3 "
            "WHEN 'Medium' THEN 2 ELSE 1 END DESC, c.priority_score DESC, c.created_at ASC")
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def list_areas() -> list:
    with get_conn() as conn:
        return [r[0] for r in conn.execute("SELECT DISTINCT area FROM complaints ORDER BY area")]


def count_complaints() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]


# ------------------------------------------------------- dashboard queries ---
def dashboard_data(date_from: str, date_to: str) -> dict:
    """The five dashboard views. Dates are 'YYYY-MM-DD' strings (inclusive)."""
    p = (date_from + " 00:00:00", date_to + " 23:59:59")
    rng = "c.created_at BETWEEN ? AND ?"
    queries = {
        "volume": f"SELECT date(c.created_at) AS day, COUNT(*) AS complaints "
                  f"FROM complaints c WHERE {rng} GROUP BY day ORDER BY day",
        "category": f"SELECT cat.name AS category, COUNT(*) AS complaints FROM complaints c "
                    f"JOIN categories cat ON cat.id = c.category_id WHERE {rng} "
                    f"GROUP BY cat.name ORDER BY complaints DESC",
        "priority": f"SELECT c.priority_label AS priority, COUNT(*) AS complaints "
                    f"FROM complaints c WHERE {rng} GROUP BY c.priority_label",
        "area": f"SELECT c.area, COUNT(*) AS complaints FROM complaints c WHERE {rng} "
                f"GROUP BY c.area ORDER BY complaints DESC LIMIT 15",
        "status": f"SELECT c.status, COUNT(*) AS complaints FROM complaints c WHERE {rng} GROUP BY c.status",
        "resolution": f"SELECT cat.name AS category, COUNT(*) AS resolved, "
                      f"ROUND(AVG((julianday(c.resolved_at) - julianday(c.created_at)) * 24), 1) AS avg_hours "
                      f"FROM complaints c JOIN categories cat ON cat.id = c.category_id "
                      f"WHERE {rng} AND c.status = 'Resolved' AND c.resolved_at IS NOT NULL "
                      f"GROUP BY cat.name ORDER BY avg_hours DESC",
    }
    with get_conn() as conn:
        return {name: pd.read_sql_query(sql, conn, params=p) for name, sql in queries.items()}


def date_range() -> tuple:
    with get_conn() as conn:
        row = conn.execute("SELECT date(MIN(created_at)), date(MAX(created_at)) FROM complaints").fetchone()
    return row[0], row[1]


# ------------------------------------------------------------ admin users ---
def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000).hex()


def create_admin(username: str, password: str) -> None:
    """Create an admin user, or reset the password if the username exists."""
    salt = secrets.token_bytes(16)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO admin_users (username, password_hash, salt) VALUES (?, ?, ?) "
            "ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash, salt = excluded.salt",
            (username, _hash_password(password, salt), salt.hex()),
        )


def verify_admin(username: str, password: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT password_hash, salt FROM admin_users WHERE username = ?", (username,)
        ).fetchone()
    if row is None:
        return False
    return hmac.compare_digest(row["password_hash"], _hash_password(password, bytes.fromhex(row["salt"])))


def admin_count() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0]
