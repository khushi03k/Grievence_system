# Run Guide: Intelligent Public Grievance Analytics and Decision Support System

Phase I Minor Project · Group 22 · CSE2 · IGDTUW

This guide takes you from nothing to the running application. Every command here was run on 24 November 2026 in a fresh environment (Python 3.12) and worked.

## 1. What you need

- Python 3.10 or newer. Check with `python --version` (Windows) or `python3 --version` (macOS/Linux).
- Internet access to install the packages.
- About 500 MB of free disk space.

## 2. Get the code

Use one of these.

**Option A (recommended): the zip file.** Unzip `grievance-system.zip`. It contains all 14 source files and the two prepared data files, so no dataset download is needed and you get exactly the results shown in this guide.

**Option B: build from the design document.** Give `Grievance_System_Design_and_Build_Document.md` to Claude (Claude Code or Cowork) and ask it to "build this project following Section 0". The data is then downloaded fresh in step 4.

Open a terminal inside the `grievance-system` folder. All commands below are run from there.

## 3. Install (once)

Windows:

```text
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -c "import nltk; nltk.download('stopwords')"
```

macOS / Linux:

```text
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -c "import nltk; nltk.download('stopwords')"
```

## 4. Prepare the data (once)

**If you used the zip, skip this step.** The files `data/training_data.csv` and `data/seed_complaints.csv` are already there.

Otherwise:

```text
python prepare_data.py
```

This downloads October 2026 of NYC 311 (about 50 MB, roughly 5 minutes). If it stops, run it again; finished days are skipped. It must end with `Done.`

## 5. Train the model (once)

The project has 15 categories. NYC 311 has no complaints for four of them (Public Health & Healthcare, Government Schemes & Social Welfare, Identity, Certificates & Citizen Services, Central Government Departments & Public Services), so their training examples are generated from templates. Create them first:

```text
python make_disaster_data.py
python make_extra_data.py
python train_model.py
```

The best model and its macro-F1 are printed at the end (target: >= 0.75). The numbers will differ from older runs because the category set changed.

The comparison table, classification reports and confusion-matrix images are written to `reports/`.

## 6. Create the database and the admin user (once)

Pick your own username and a password of at least 8 characters:

```text
python setup_database.py admin YourPassword123
```

Expected:

```text
Loaded 12000 complaints
Admin user 'admin' created
```

Warning: running this again deletes the database and rebuilds it.

## 7. Check that everything works

```text
python -m pytest -v
python check_performance.py
```

Expected: `7 passed`, and `Target (>= 10,000 records, < 3 seconds): MET`.

## 8. Start the application

```text
streamlit run app.py
```

The browser opens at `http://localhost:8501`. To stop, press `Ctrl + C` in the terminal.

**Every later time** you only need two commands:

```text
venv\Scripts\activate          (Windows)   or   source venv/bin/activate   (macOS/Linux)
streamlit run app.py
```

## 9. Demonstration and acceptance checklist

Go through these in the running app. The expected results were confirmed in testing.

| # | Do this | You should see |
|---|---|---|
| 1 | Submit Complaint: type "short", leave area empty, submit | Two red error messages; nothing saved |
| 2 | Submit: "Sewer is overflowing in front of the school gate", area "Ward 5" | Green message with an ID like `GRV-1A2B3C4D`; category Sewerage & Drainage; priority High |
| 3 | Submit: "Loud music from neighbours every night after midnight", area "Ward 2" | Category Noise Pollution; priority Low |
| 4 | Track Complaint: paste the ID from step 2 | Status Open, the category and priority, one row of history |
| 5 | Analytics Dashboard without logging in | Login form |
| 6 | Log in with a wrong password | "Invalid username or password." |
| 7 | Log in with your admin username and password | Dashboard with four counters and five numbered views |
| 8 | Change the From / To dates | Counters and charts change |
| 9 | Admin Console: set Priority filter to High | Shorter list, all High |
| 10 | Type "school gate" in Search | The complaint from step 2 |
| 11 | Click "Export filtered complaints as CSV" | A CSV file downloads |
| 12 | Paste the step 2 ID into "Complaint ID to update" | Complaint details and the line "Rule-based score: 0.4 x 0.80 (severity) + 0.3 x 0.60 (urgency) + 0.2 x 1.00 (area) + ... = 0.7 -> High" |
| 13 | Set Status to Resolved, Category to Public Safety & Emergency Services, Priority to Critical; Save changes | "Changes saved."; status history shows Open then Resolved; override log shows two rows with your admin name |
| 14 | Click "Update ageing score of open complaints" | "Priority recalculated for ... open complaints." |
| 15 | Log out (sidebar) | Dashboard and Admin Console ask for login again |

## 10. One manual task: validate the priority rules

The synopsis asks for the priority rules to be checked against at least 100 manually labelled complaints (target: 80% agreement). Only people can do the labelling.

```text
python validate_priority.py export
```

Open `data/priority_validation_sample.csv` in Excel or Google Sheets. For each of the 100 rows type `Low`, `Medium`, `High` or `Critical` in the `human_priority` column, using your own judgement. Save as CSV with the same name. Then:

```text
python validate_priority.py evaluate
```

The agreement percentage and a comparison table are printed and saved to `reports/priority_validation.txt`. If it is below 80%, adjust the severity values or keywords in `config.py` with your guide and evaluate again.

## 11. If something goes wrong

| Problem | Fix |
|---|---|
| `python` is not recognised | Install Python from python.org and tick "Add Python to PATH"; on macOS/Linux use `python3`. |
| PowerShell refuses to run `activate` | Use Command Prompt, or run `Set-ExecutionPolicy -Scope Process RemoteSigned` first. |
| `ModuleNotFoundError` | The virtual environment is not active. Activate it (step 3) and run `pip install -r requirements.txt`. |
| The app says "The system is not set up yet" | Run steps 5 and 6, then restart the app. |
| `prepare_data.py` prints "attempt 1 failed" | Normal on a slow connection; it retries. If it ends with "Download failed", run it again. |
| Port 8501 is busy | `streamlit run app.py --server.port 8502` |
| Forgotten admin password | `python -c "import database as db; db.create_admin('admin', 'NewPassword123')"` (keeps all complaints) |
| Start again from zero | Delete the `models` and `reports` folders and the file `data/grievance.db`, then repeat from step 5. |

## 12. Where things are

| File | Part |
|---|---|
| `app.py` | Frontend: submission form, tracking, analytics dashboard, admin console |
| `database.py`, `setup_database.py` | Backend: SQL schema, all queries, admin login |
| `preprocess.py`, `prepare_data.py`, `train_model.py`, `classifier.py` | Machine learning: cleaning, dataset, training and comparison, prediction |
| `priority.py`, `validate_priority.py` | Priority scoring and its validation |
| `config.py` | All settings (categories, severity, keywords, weights, thresholds) |
| `tests/test_core.py`, `check_performance.py` | Tests and dashboard speed check |
