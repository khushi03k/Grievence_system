"""Checks objective 2: dashboard queries must return in under 3 seconds on >= 10,000 records.

Run:  python check_performance.py
"""
import time

import database as db

records = db.count_complaints()
first, last = db.date_range()
start = time.perf_counter()
db.dashboard_data(first, last)
elapsed = time.perf_counter() - start

print(f"Records in database: {records}")
print(f"Time for all dashboard queries: {elapsed:.3f} seconds")
print(f"Target (>= 10,000 records, < 3 seconds): {'MET' if records >= 10000 and elapsed < 3 else 'NOT MET'}")
