"""Step 1: download NYC 311 data and map it to the unified category set.

Downloads one month of service requests, one day per request (each day is saved
in data/raw/, so an interrupted run continues where it stopped), then creates:
  data/training_data.csv    unique complaint texts with a unified category (for the classifier)
  data/seed_complaints.csv  a random sample of real requests used to fill the database

Run:  python prepare_data.py
"""
import time
from datetime import date, timedelta

import pandas as pd
import requests

import config
from preprocess import clean_text

COLUMNS = ("unique_key,created_date,closed_date,complaint_type,descriptor,"
           "descriptor_2,location_type,borough,status")
MAX_ROWS_PER_DAY = 50000


def download_day(day: date) -> None:
    """Download all service requests created on one day (3 attempts)."""
    target = config.RAW_DIR / f"{day}.csv"
    if target.exists():
        return
    next_day = day + timedelta(days=1)
    params = {
        "$select": COLUMNS,
        "$where": f"created_date >= '{day}T00:00:00' AND created_date < '{next_day}T00:00:00'",
        "$limit": MAX_ROWS_PER_DAY,
    }
    for attempt in range(1, 4):
        try:
            r = requests.get(config.NYC311_URL, params=params, timeout=120)
            r.raise_for_status()
            if not r.text.rstrip().endswith('"'):
                raise ValueError("incomplete download")
            target.write_text(r.text, encoding="utf-8")
            print(f"  {day}: {r.text.count(chr(10)) - 1} rows")
            return
        except Exception as exc:  # network error or incomplete download
            print(f"  {day}: attempt {attempt} failed ({exc})")
            time.sleep(5)
    raise SystemExit("Download failed. Check the internet connection and run this script again.")


def load_raw() -> pd.DataFrame:
    files = sorted(config.RAW_DIR.glob("*.csv"))
    df = pd.concat((pd.read_csv(f, dtype=str, keep_default_na=False) for f in files), ignore_index=True)
    return df.drop_duplicates("unique_key")


def build_text(df: pd.DataFrame) -> pd.Series:
    """Join the descriptive fields of a 311 record into one complaint text."""
    def join(row):
        parts = [row["descriptor"], row["descriptor_2"], row["location_type"]]
        return ". ".join(p.strip() for p in parts if p.strip() and p.strip().upper() != "N/A")
    return df.apply(join, axis=1)


def make_training_data(df: pd.DataFrame) -> None:
    # Keep every cleaned text once. If the same text appears under two categories,
    # keep the category under which it was reported most often.
    counts = (df.groupby(["clean_text", "category"], as_index=False)
                .agg(text=("text", "first"), n=("text", "size"))
                .sort_values("n", ascending=False)
                .drop_duplicates("clean_text"))
    counts[["text", "clean_text", "category", "n"]].to_csv(config.TRAIN_CSV, index=False)
    print(f"\n{len(counts)} unique labelled texts saved to {config.TRAIN_CSV}")
    print(counts["category"].value_counts().to_string())


def make_seed_data(df: pd.DataFrame) -> None:
    df = df.copy()
    df["created_at"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["resolved_at"] = pd.to_datetime(df["closed_date"].replace("", None), errors="coerce")
    df = df.dropna(subset=["created_at"])
    closed = df["status"].str.lower() == "closed"
    # drop closed records that have no valid closing time
    df = df[~closed | (df["resolved_at"] >= df["created_at"])].copy()
    closed = df["status"].str.lower() == "closed"
    df["new_status"] = "Open"
    df.loc[df["status"].str.lower() == "in progress", "new_status"] = "In Progress"
    df.loc[closed, "new_status"] = "Resolved"
    df.loc[~closed, "resolved_at"] = pd.NaT
    df["area"] = df["borough"].str.title().replace("", "Unspecified")

    df = df.sample(config.SEED_RECORDS, random_state=config.RANDOM_STATE).sort_values("created_at")
    out = df[["unique_key", "created_at", "resolved_at", "text", "area", "category", "new_status"]]
    out = out.rename(columns={"new_status": "status"})
    out.to_csv(config.SEED_CSV, index=False, date_format="%Y-%m-%d %H:%M:%S")
    print(f"\n{len(out)} records saved to {config.SEED_CSV}")
    print(out["status"].value_counts().to_string())


if __name__ == "__main__":
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    start = date.fromisoformat(config.DATA_START)
    print(f"Downloading NYC 311 data for {config.DATA_DAYS} days from {start}...")
    for i in range(config.DATA_DAYS):
        download_day(start + timedelta(days=i))

    raw = load_raw()
    raw["category"] = raw["complaint_type"].str.lower().str.strip().map(config.COMPLAINT_TYPE_TO_CATEGORY)
    data = raw.dropna(subset=["category"]).copy()
    data["text"] = build_text(data)
    data["clean_text"] = data["text"].map(clean_text)
    data = data[data["clean_text"] != ""]
    print(f"\n{len(raw)} rows downloaded, {len(data)} rows map to the {len(config.CATEGORIES)} unified categories")

    make_training_data(data)
    make_seed_data(data)
    print("\nDone.")
