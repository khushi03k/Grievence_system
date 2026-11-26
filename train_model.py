"""Step 2: train and compare three classical classifiers on TF-IDF features.

Compares Multinomial Naive Bayes, Logistic Regression and Linear SVM using a
stratified train/test split and 5-fold cross-validation, writes the comparison
to reports/ and saves the best model (highest cross-validated macro-F1).

Run:  python train_model.py
"""
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, classification_report,
                             precision_recall_fscore_support)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

import config

MODELS = {
    # Naive Bayes has no class_weight option; the other two use balanced class weights.
    "Multinomial Naive Bayes": MultinomialNB(),
    "Logistic Regression": LogisticRegression(class_weight="balanced", max_iter=2000),
    "Linear SVM": LinearSVC(class_weight="balanced"),
}


def make_pipeline(classifier) -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
        ("clf", classifier),
    ])


def main() -> None:
    if not config.TRAIN_CSV.exists():
        raise SystemExit("data/training_data.csv not found. Run: python prepare_data.py")
    config.MODEL_DIR.mkdir(exist_ok=True)
    config.REPORT_DIR.mkdir(exist_ok=True)

    df = pd.read_csv(config.TRAIN_CSV)
    # Template-generated examples: disasters (make_disaster_data.py) and the categories
    # NYC 311 does not cover (make_extra_data.py).
    for name in ("disaster_examples.csv", "extra_examples.csv"):
        extra = config.DATA_DIR / name
        if extra.exists():
            df = pd.concat([df, pd.read_csv(extra)], ignore_index=True)
    df = df.dropna(subset=["clean_text", "category"]).drop_duplicates("clean_text")
    X, y = df["clean_text"], df["category"]
    # Every text is unique, so no test text has been seen during training.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=config.RANDOM_STATE)
    print(f"{len(df)} unique texts: {len(X_train)} train / {len(X_test)} test, {y.nunique()} categories\n")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=config.RANDOM_STATE)
    rows, fitted = [], {}
    for name, clf in MODELS.items():
        pipe = make_pipeline(clf)
        cv_f1 = cross_val_score(pipe, X_train, y_train, cv=cv, scoring="f1_macro")
        pipe.fit(X_train, y_train)
        pred = pipe.predict(X_test)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, pred, average="macro", zero_division=0)
        rows.append({
            "model": name,
            "cv_macro_f1_mean": round(cv_f1.mean(), 4),
            "cv_macro_f1_std": round(cv_f1.std(), 4),
            "test_accuracy": round(accuracy_score(y_test, pred), 4),
            "test_macro_precision": round(precision, 4),
            "test_macro_recall": round(recall, 4),
            "test_macro_f1": round(f1, 4),
        })
        fitted[name] = pipe

        slug = name.lower().replace(" ", "_")
        report = classification_report(y_test, pred, zero_division=0)
        (config.REPORT_DIR / f"classification_report_{slug}.txt").write_text(report)
        fig, ax = plt.subplots(figsize=(9, 8))
        ConfusionMatrixDisplay.from_predictions(
            y_test, pred, ax=ax, xticks_rotation=45, colorbar=False, cmap="Blues")
        ax.set_title(f"Confusion matrix - {name}")
        fig.tight_layout()
        fig.savefig(config.REPORT_DIR / f"confusion_matrix_{slug}.png", dpi=150)
        plt.close(fig)

    results = pd.DataFrame(rows).sort_values("cv_macro_f1_mean", ascending=False)
    results.to_csv(config.REPORT_DIR / "model_comparison.csv", index=False)
    print(results.to_string(index=False))

    best = results.iloc[0]
    joblib.dump({"name": best["model"], "pipeline": fitted[best["model"]]}, config.MODEL_PATH)
    print(f"\nBest model: {best['model']} (test macro-F1 = {best['test_macro_f1']})")
    print(f"Target macro-F1 >= 0.75: {'MET' if best['test_macro_f1'] >= 0.75 else 'NOT MET'}")
    print(f"Saved to {config.MODEL_PATH}; reports are in {config.REPORT_DIR}")


if __name__ == "__main__":
    main()
