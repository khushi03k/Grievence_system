"""Loads the trained model and predicts the category of a complaint."""
import joblib

import config
from preprocess import clean_text

_bundle = None


def model_available() -> bool:
    return config.MODEL_PATH.exists()


def _load():
    global _bundle
    if _bundle is None:
        _bundle = joblib.load(config.MODEL_PATH)
    return _bundle


def model_name() -> str:
    return _load()["name"]


def predict_category(text: str) -> str:
    return str(_load()["pipeline"].predict([clean_text(text)])[0])
