"""Creates data/disaster_examples.csv: labelled complaints for the 'Public Safety & Emergency Services' category.

NYC 311 has no natural-disaster complaints, so these examples are generated from
templates (event x impact x place) and merged into the training data by train_model.py.

Run:  python make_disaster_data.py
"""
import itertools
import random

import pandas as pd

import config
from preprocess import clean_text

EVENTS = [
    "earthquake", "strong earthquake", "earthquake tremors", "aftershocks after the earthquake",
    "landslide", "flash flood", "heavy flooding", "cloudburst", "cyclone", "storm damage",
    "tsunami warning", "hailstorm", "cold wave", "heat wave", "drought", "avalanche",
    "forest fire", "building collapsed after earthquake", "river overflow flood", "thunderstorm lightning strike",
]
IMPACTS = [
    "cracks in houses", "people trapped under debris", "buildings damaged", "families left homeless",
    "need rescue team", "roads blocked", "no relief camp nearby", "need food and drinking water",
    "injured people need medical help", "village cut off", "walls collapsed", "crops destroyed",
    "need evacuation", "power lines fallen", "animals died", "request emergency relief",
]
PLACES = [
    "in our colony", "near the school", "in our village", "in the main market", "near the hospital",
    "in sector 12", "in the whole neighbourhood", "on the hill road", "near the river bank", "in our area",
]
SHORT = [
    "earthquake", "earthquake in our area", "felt strong earthquake tremors", "earthquake damage",
    "landslide on the road", "flood in our locality", "cyclone damage", "natural disaster relief needed",
    "disaster management team needed", "earthquake relief request", "flood relief request",
    "tremors felt, please check buildings", "heavy rain flood and landslide", "house damaged in earthquake",
]


def main() -> None:
    rng = random.Random(config.RANDOM_STATE)
    combos = list(itertools.product(EVENTS, IMPACTS, PLACES))
    rng.shuffle(combos)
    texts = [f"{e.capitalize()} {p}, {i}" for e, i, p in combos[:350]] + [t.capitalize() for t in SHORT]
    rows = {clean_text(t): t for t in texts}
    df = pd.DataFrame({"text": list(rows.values()), "clean_text": list(rows.keys())})
    df["category"] = "Public Safety & Emergency Services"
    df["n"] = 1
    out = config.DATA_DIR / "disaster_examples.csv"
    df.to_csv(out, index=False)
    print(f"{len(df)} examples saved to {out}")


if __name__ == "__main__":
    main()
