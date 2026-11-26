"""Step 3: create the database, load the seed complaints and create an admin user.

Run:  python setup_database.py <admin_username> <admin_password>
Re-running it deletes the existing database and builds it again.
"""
import sys
from datetime import datetime

import pandas as pd

import config
import database as db
from priority import score_complaint


def load_seed_complaints() -> int:
    df = pd.read_csv(config.SEED_CSV, dtype=str, keep_default_na=False)
    now = datetime.now()
    used_codes = set()
    with db.get_conn() as conn:
        cat_ids = db.category_ids(conn)
        for row in df.itertuples(index=False):
            created = datetime.strptime(row.created_at, "%Y-%m-%d %H:%M:%S")
            days_open = 0.0 if row.status == "Resolved" else (now - created).total_seconds() / 86400
            result = score_complaint(row.text, row.category, row.area, days_open)
            code = db.new_complaint_code()
            while code in used_codes:
                code = db.new_complaint_code()
            used_codes.add(code)
            resolved_at = row.resolved_at or None
            cur = conn.execute(
                "INSERT INTO complaints (complaint_code, text, area, contact, category_id, priority_score, "
                "priority_label, status, created_at, updated_at, resolved_at) "
                "VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)",
                (code, row.text, row.area, cat_ids[row.category], result["score"], result["label"],
                 row.status, row.created_at, resolved_at or row.created_at, resolved_at),
            )
            history = [(cur.lastrowid, None, "Open", "import", row.created_at)]
            if row.status == "Resolved":
                history.append((cur.lastrowid, "Open", "Resolved", "import", resolved_at))
            elif row.status == "In Progress":
                history.append((cur.lastrowid, "Open", "In Progress", "import", row.created_at))
            conn.executemany(
                "INSERT INTO status_history (complaint_id, old_status, new_status, changed_by, changed_at) "
                "VALUES (?, ?, ?, ?, ?)", history)
    return len(df)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python setup_database.py <admin_username> <admin_password>")
    username, password = sys.argv[1], sys.argv[2]
    if len(password) < 8:
        raise SystemExit("The admin password must have at least 8 characters.")
    if not config.SEED_CSV.exists():
        raise SystemExit("data/seed_complaints.csv not found. Run: python prepare_data.py")

    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
    db.init_db()
    print(f"Database created at {config.DB_PATH}")
    print(f"Loaded {load_seed_complaints()} complaints")
    db.create_admin(username, password)
    print(f"Admin user '{username}' created")


if __name__ == "__main__":
    main()
