"""Central configuration: paths, categories, priority rules and dataset settings.

Every value that the guide may want to tune (weights, severities, keywords,
thresholds) lives in this one file.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
REPORT_DIR = BASE_DIR / "reports"

RAW_DIR = DATA_DIR / "raw"

DB_PATH = DATA_DIR / "grievance.db"
TRAIN_CSV = DATA_DIR / "training_data.csv"
SEED_CSV = DATA_DIR / "seed_complaints.csv"
MODEL_PATH = MODEL_DIR / "best_model.joblib"
PRIORITY_SAMPLE_CSV = DATA_DIR / "priority_validation_sample.csv"

# ---------------------------------------------------------------- dataset ---
# NYC 311 Service Requests (NYC Open Data), the dataset named in the synopsis.
NYC311_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.csv"
# Fixed dates so that every run downloads the same data: all of October 2026.
DATA_START = "2026-10-01"
DATA_DAYS = 31
SEED_RECORDS = 12000          # records loaded into the database (objective: >= 10,000)
RANDOM_STATE = 42

# ------------------------------------------------------------- categories ---
CATEGORY_SEVERITY = {
    "Water Supply": 0.8,
    "Sewerage & Drainage": 0.8,
    "Roads & Infrastructure": 0.7,
    "Sanitation & Waste Management": 0.7,
    "Electricity & Street Lighting": 0.8,
    "Public Health & Healthcare": 0.9,
    "Public Safety & Emergency Services": 1.0,
    "Traffic & Transportation": 0.7,
    "Environment, Parks & Trees": 0.5,
    "Housing & Building Services": 0.7,
    "Noise Pollution": 0.3,
    "Encroachment & Public Land": 0.6,
    "Government Schemes & Social Welfare": 0.6,
    "Identity, Certificates & Citizen Services": 0.4,
    "Central Government Departments & Public Services": 0.6,
}
CATEGORIES = list(CATEGORY_SEVERITY)

_TYPE_GROUPS = {
    "Noise Pollution": [
        "noise", "noise - residential", "noise - street/sidewalk", "noise - commercial",
        "noise - vehicle", "noise - park", "noise - helicopter", "noise - house of worship",
    ],
    "Roads & Infrastructure": [
        "street condition", "sidewalk condition", "curb condition", "highway condition",
        "bridge condition", "street sign - damaged", "street sign - missing",
        "street sign - dangling", "highway sign - damaged", "highway sign - missing",
        "highway sign - dangling", "root/sewer/sidewalk condition",
    ],
    "Traffic & Transportation": [
        "traffic signal condition", "traffic", "bus stop shelter complaint",
        "illegal parking", "blocked driveway", "abandoned vehicle", "derelict vehicles",
        "broken parking meter", "abandoned bike",
    ],
    "Encroachment & Public Land": ["obstruction", "encroachment"],
    "Electricity & Street Lighting": ["street light condition", "electric", "electrical"],
    "Water Supply": [
        "water maintenance", "water system", "water leak", "plumbing", "water conservation",
        "water quality", "drinking water",
    ],
    "Sewerage & Drainage": ["sewer maintenance", "sewer", "standing water", "indoor sewage"],
    # "Sanitation & Waste Management", "Housing & Building Services",
    # "Environment, Parks & Trees", "Public Safety & Emergency Services":
    # purani lists waise hi rakho, bas key ka naam naya karo
}
COMPLAINT_TYPE_TO_CATEGORY = {t: cat for cat, types in _TYPE_GROUPS.items() for t in types}

# --------------------------------------------------------------- priority ---
# P = 0.4*Sc + 0.3*Su + 0.2*Sa + 0.1*St   (formula from the synopsis)
WEIGHTS = {"severity": 0.4, "urgency": 0.3, "area": 0.2, "ageing": 0.1}

# Su: urgency keywords found in the complaint text.
URGENCY_CRITICAL = [  # Su = 1.0
    "fire", "electrocution", "electric shock", "live wire", "gas leak", "collapse",
    "collapsed", "accident", "flood", "flooding", "emergency", "danger", "dangerous",
    "life threatening", "explosion", "sparking",
    "earthquake", "tremor", "tremors", "landslide", "cyclone", "tsunami", "cloudburst",
    "trapped", "flash flood",
]
URGENCY_HIGH = [      # Su = 0.6
    "urgent", "immediately", "hazard", "unsafe", "injury", "injured", "leak", "leaking",
    "overflow", "overflowing", "no water", "no heat", "no electricity", "fallen",
    "exposed", "contaminated", "sewage",
]

# Sa: sensitive location or wide affected area, searched in the text and the area field.
SENSITIVE_LOCATIONS = [  # Sa = 1.0
    "hospital", "school", "college", "clinic", "nursing home", "day care", "daycare",
    "playground", "market", "station", "highway", "main road", "intersection", "bridge",
]
WIDE_AREA = [            # Sa = 0.6
    "entire", "whole", "all residents", "many people", "colony", "neighbourhood",
    "neighborhood", "building-wide", "multiple",
]

AGEING_FULL_DAYS = 7     # St reaches 1.0 when a complaint has been open this many days

# (label, lower bound) checked from the top: Critical >= 0.8, High >= 0.6, Medium >= 0.3
PRIORITY_THRESHOLDS = [("Critical", 0.8), ("High", 0.6), ("Medium", 0.3), ("Low", 0.0)]
PRIORITY_LEVELS = ["Low", "Medium", "High", "Critical"]

STATUSES = ["Open", "In Progress", "Resolved"]
