"""Text cleaning used for both training and live prediction."""
import re

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer

try:
    _STOP_WORDS = set(stopwords.words("english"))
except LookupError:  # first run: download the stop-word list once
    nltk.download("stopwords", quiet=True)
    _STOP_WORDS = set(stopwords.words("english"))

# Negations change the meaning of a complaint ("no water"), so they are kept.
_STOP_WORDS -= {"no", "not"}
_TOKENIZER = RegexpTokenizer(r"[a-z]+")


def clean_text(text) -> str:
    """Lower-case, remove punctuation/digits, tokenise and drop stop words."""
    if not isinstance(text, str):
        return ""
    tokens = _TOKENIZER.tokenize(text.lower())
    return " ".join(t for t in tokens if t not in _STOP_WORDS and len(t) > 1)


def contains_keyword(text: str, keywords) -> bool:
    """True if any keyword/phrase appears in the text as a whole word."""
    text = (text or "").lower()
    return any(re.search(r"\b" + re.escape(k) + r"\b", text) for k in keywords)
