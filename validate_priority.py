"""Step 5: validate the priority rules against manually labelled complaints.

  python validate_priority.py export     writes data/priority_validation_sample.csv (100 complaints)
  (team members fill the 'human_priority' column: Low, Medium, High or Critical)
  python validate_priority.py evaluate   compares the rules with the human labels

The rule-based priority is computed without ageing (St = 0), because a person
labelling the text alone cannot know how long the complaint has been open.
"""
import sys

import pandas as pd

import config
import database as db
from priority import score_complaint

SAMPLE_SIZE = 100


def export() -> None:
    if config.PRIORITY_SAMPLE_CSV.exists():
        raise SystemExit(f"{config.PRIORITY_SAMPLE_CSV} already exists. Delete it first to create a new sample.")
    df = db.fetch_complaints()
    df["rule"] = [score_complaint(r.text, r.category, r.area)["label"] for r in df.itertuples()]
    # take complaints from every priority level, then fill up randomly to 100
    per_level = SAMPLE_SIZE // len(config.PRIORITY_LEVELS)
    picked = pd.concat([g.sample(min(len(g), per_level), random_state=config.RANDOM_STATE)
                        for _, g in df.groupby("rule")])
    rest = df.drop(picked.index).sample(SAMPLE_SIZE - len(picked), random_state=config.RANDOM_STATE)
    sample = pd.concat([picked, rest]).sample(frac=1, random_state=config.RANDOM_STATE)
    sample = sample[["complaint_code", "text", "area", "category"]].copy()
    sample["human_priority"] = ""
    sample.to_csv(config.PRIORITY_SAMPLE_CSV, index=False)
    print(f"{len(sample)} complaints written to {config.PRIORITY_SAMPLE_CSV}")
    print("Fill the 'human_priority' column with Low, Medium, High or Critical, then run:")
    print("  python validate_priority.py evaluate")


def evaluate() -> None:
    if not config.PRIORITY_SAMPLE_CSV.exists():
        raise SystemExit("Sample file not found. Run: python validate_priority.py export")
    df = pd.read_csv(config.PRIORITY_SAMPLE_CSV, dtype=str, keep_default_na=False)
    df["human_priority"] = df["human_priority"].str.strip().str.title()
    invalid = df[~df["human_priority"].isin(config.PRIORITY_LEVELS)]
    if len(invalid):
        raise SystemExit(f"{len(invalid)} rows have no valid human_priority "
                         f"(allowed: {', '.join(config.PRIORITY_LEVELS)}). Fill them and run again.")
    df["rule_priority"] = [score_complaint(r.text, r.category, r.area)["label"] for r in df.itertuples()]
    agreement = (df["human_priority"] == df["rule_priority"]).mean() * 100
    table = pd.crosstab(df["human_priority"], df["rule_priority"]).reindex(
        index=config.PRIORITY_LEVELS, columns=config.PRIORITY_LEVELS, fill_value=0)
    report = (f"Priority rule validation on {len(df)} manually labelled complaints\n"
              f"Agreement: {agreement:.1f}%  (target >= 80%: {'MET' if agreement >= 80 else 'NOT MET'})\n\n"
              f"Rows = human label, columns = rule-based label\n{table.to_string()}\n")
    config.REPORT_DIR.mkdir(exist_ok=True)
    (config.REPORT_DIR / "priority_validation.txt").write_text(report)
    print(report)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "export":
        export()
    elif len(sys.argv) == 2 and sys.argv[1] == "evaluate":
        evaluate()
    else:
        raise SystemExit("Usage: python validate_priority.py export | evaluate")
