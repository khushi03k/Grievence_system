"""Unit and integration tests. Run:  python -m pytest -v"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import database as db
from preprocess import clean_text
from priority import label_for, score_complaint


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Every test gets its own empty database."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    db.init_db()


def test_clean_text():
    assert clean_text("The Street-Light is NOT working!!! 123") == "street light not working"
    assert clean_text(None) == ""


def test_priority_labels():
    assert label_for(0.29) == "Low"
    assert label_for(0.3) == "Medium"
    assert label_for(0.6) == "High"
    assert label_for(0.8) == "Critical"


def test_priority_formula():
    r = score_complaint("Live wire fallen near the school gate", "Electricity & Street Lighting", "Ward 5")
    # 0.4*0.8 + 0.3*1.0 + 0.2*1.0 + 0.1*0 = 0.82
    assert r["score"] == 0.82 and r["label"] == "Critical"
    r = score_complaint("Loud music at night", "Noise Pollution", "Ward 5")
    assert r["score"] == 0.12 and r["label"] == "Low"


def test_ageing_raises_score():
    fresh = score_complaint("Garbage not collected", "Sanitation & Waste Management", "Ward 2", days_open=0)
    old = score_complaint("Garbage not collected", "Sanitation & Waste Management", "Ward 2", days_open=7)
    assert round(old["score"] - fresh["score"], 3) == 0.1


def test_submit_and_track(temp_db):
    code = db.insert_complaint("Water pipe leaking on the road", "Ward 1", "", "Water Supply", 0.5, "Medium")
    other = db.insert_complaint("Loud music at night", "Ward 2", "", "Noise Pollution", 0.12, "Low")
    assert code.startswith("GRV-") and code != other
    c = db.get_complaint(code)
    assert c["status"] == "Open" and c["category"] == "Water Supply" and c["created_at"]
    assert db.count_complaints() == 2


def test_status_update_and_overrides_are_logged(temp_db):
    code = db.insert_complaint("Pothole on main road", "Ward 3", "", "Roads & Infrastructure", 0.4, "Medium")
    db.update_status(code, "Resolved", "admin1")
    db.override_category(code, "Public Safety & Emergency Services", "admin1")
    db.override_priority(code, "High", "admin1")
    c = db.get_complaint(code)
    assert c["status"] == "Resolved" and c["resolved_at"] is not None
    assert c["category"] == "Public Safety & Emergency Services" and c["priority_label"] == "High"
    assert list(db.get_status_history(code)["new_status"]) == ["Open", "Resolved"]
    assert list(db.get_override_log(code)["field"]) == ["category", "priority"]


def test_admin_login(temp_db):
    db.create_admin("admin1", "secret-password")
    assert db.verify_admin("admin1", "secret-password")
    assert not db.verify_admin("admin1", "wrong")
    assert not db.verify_admin("nobody", "secret-password")
