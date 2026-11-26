"""Creates data/extra_examples.csv: labelled complaints for categories NYC 311 does not cover.

Covers Public Health & Healthcare, Government Schemes & Social Welfare,
Identity, Certificates & Citizen Services, Central Government Departments & Public
Services, and adds extra Encroachment & Public Land examples. Texts are generated
from templates (issue x place) and merged into the training data by train_model.py.

Run:  python make_extra_data.py
"""
import itertools
import random

import pandas as pd

import config
from preprocess import clean_text

PLACES = [
    "in our colony", "near the school", "in our village", "in ward 5", "near the main market",
    "in sector 12", "in our locality", "near the bus stand", "in our area", "since last month",
]

ISSUES = {
    "Public Health & Healthcare": [
        "No doctor available at the government hospital", "Medicines not available at the dispensary",
        "Primary health centre is always closed", "Ambulance did not arrive on time",
        "Dengue cases rising and no fogging done", "Malaria outbreak due to stagnant water",
        "Cholera and diarrhoea cases reported", "Vaccination camp not organised for children",
        "Long waiting time at civil hospital", "Hospital staff misbehaving with patients",
        "No beds available in the government hospital", "Mohalla clinic has no doctor",
        "Free medical tests not provided at the hospital", "Blood bank has no blood stock",
        "Mosquito breeding and fever cases", "Food poisoning cases after a community event",
        "Ayushman Bharat card not accepted at the hospital", "Expired medicines given at the health centre",
        "Pregnant women not getting antenatal check-ups", "Nurse and ANM not visiting the village",
        "Medical shop selling medicines above the printed price", "Hospital is unhygienic and dirty",
    ],
    "Government Schemes & Social Welfare": [
        "Old age pension not received for months", "Widow pension has been stopped",
        "Ration card holders not getting wheat and rice", "Ration shop owner refuses to give full quota",
        "Not receiving PM Kisan instalment", "Scholarship amount not credited to the student",
        "Applied for housing scheme but no response", "Ujjwala gas connection not given",
        "Disability pension application is pending", "Mid-day meal not served in the school",
        "MGNREGA wages not paid", "Name missing from the beneficiary list",
        "Ladli scheme money not received", "Free ration is being denied to eligible families",
        "Labour card benefits not given", "Anganwadi is not providing nutrition food",
        "Subsidy under the scheme not released", "Application for the welfare scheme rejected without reason",
        "Pension office asks for bribe to release payment", "Student stipend for SC ST category pending",
        "Jan Dhan account benefit not received", "Maternity benefit scheme payment delayed",
    ],
    "Identity, Certificates & Citizen Services": [
        "Aadhaar card correction not done", "Aadhaar update pending for long time",
        "Birth certificate not issued", "Death certificate application pending",
        "Caste certificate delayed", "Income certificate not issued",
        "Domicile certificate is pending", "Voter ID card has wrong details",
        "Name correction needed in the voter list", "Marriage certificate not issued",
        "Driving licence not delivered", "Residence proof certificate rejected",
        "Ration card name correction not done", "PAN card not received",
        "Passport police verification is delayed", "Property tax receipt not generated online",
        "Trade licence renewal is pending", "Certificate issued with wrong spelling",
        "Office staff not accepting the application for certificate", "Online portal for certificates is not working",
        "Mutation of land records pending", "Senior citizen card application pending",
    ],
    "Central Government Departments & Public Services": [
        "Railway station has no clean drinking water", "Train is always late and no announcement",
        "Post office not delivering letters", "Speed post parcel is lost",
        "Income tax refund is pending", "Passport office staff are not responding",
        "Bank branch is not providing services", "BSNL landline and broadband not working",
        "Mobile tower signal is very poor", "LPG cylinder delivery delayed by the gas agency",
        "EPF withdrawal claim pending", "Pension from EPFO not received",
        "Railway reservation counter staff misbehaving", "Ticket refund not received from IRCTC",
        "Customs office asking for extra payment", "Central government office is closed during working hours",
        "Metro and railway enquiry counter not helping", "GST registration is stuck for weeks",
        "Aadhaar seva kendra is closed", "National highway toll plaza overcharging",
        "Airport authority not responding to complaint", "Public sector bank refusing to open an account",
    ],
    "Encroachment & Public Land": [
        "Illegal encroachment on the footpath", "Shopkeepers have occupied the pavement",
        "Illegal construction on government land", "Street vendors blocking the road",
        "Park land has been occupied illegally", "Illegal shed built on public land",
        "Encroachment on the drain and nala", "Boundary wall built on the public road",
        "Unauthorised stalls on the sidewalk", "Pond land is being occupied",
        "Illegal extension of the shop on the road", "Temple built on the road without permission",
        "Public ground has been grabbed by a builder", "Illegal hawkers on the main road",
        "Goods kept on the pavement by the shop", "Encroachment on the service lane",
        "Land mafia occupying the village common land", "Illegal parking lot made on public land",
    ],
}
SHORT = {
    "Public Health & Healthcare": ["hospital has no doctor", "need ambulance", "medicine not available", "dengue outbreak", "health centre closed"],
    "Government Schemes & Social Welfare": ["pension not received", "ration card problem", "scholarship not credited", "scheme benefit not received", "ration not given"],
    "Identity, Certificates & Citizen Services": ["aadhaar correction", "birth certificate pending", "caste certificate delay", "voter id correction", "income certificate not issued"],
    "Central Government Departments & Public Services": ["post office problem", "railway complaint", "income tax refund pending", "epfo claim pending", "bsnl line not working"],
    "Encroachment & Public Land": ["illegal encroachment", "footpath encroachment", "land grabbing", "illegal occupation of public land", "encroachment on road"],
}


def main() -> None:
    rng = random.Random(config.RANDOM_STATE)
    rows = []
    for category, issues in ISSUES.items():
        combos = list(itertools.product(issues, PLACES))
        rng.shuffle(combos)
        texts = [f"{i} {p}" for i, p in combos[:250]] + [t.capitalize() for t in SHORT[category]]
        rows += [(t, clean_text(t), category) for t in texts]
    df = pd.DataFrame(rows, columns=["text", "clean_text", "category"])
    df = df[df["clean_text"] != ""].drop_duplicates("clean_text")
    df["n"] = 1
    out = config.DATA_DIR / "extra_examples.csv"
    df.to_csv(out, index=False)
    print(f"{len(df)} examples saved to {out}")
    print(df["category"].value_counts().to_string())


if __name__ == "__main__":
    main()
