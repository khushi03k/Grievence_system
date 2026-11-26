"""Streamlit application: complaint submission, tracking, analytics dashboard and admin console.

Run:  streamlit run app.py
"""
import re
import time
from datetime import date, datetime

import plotly.express as px
import streamlit as st

import classifier
import config
import database as db
from priority import score_complaint

st.set_page_config(page_title="Public Grievance System", layout="wide")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\d{10}$")
PRIORITY_COLOURS = {"Low": "#4caf50", "Medium": "#ffc107", "High": "#ff9800", "Critical": "#f44336"}


def validate_submission(text: str, area: str, contact: str) -> list:
    errors = []
    if len(text) < 10:
        errors.append("Please describe the complaint in at least 10 characters.")
    if len(text) > 2000:
        errors.append("The complaint text must be at most 2000 characters.")
    if not 2 <= len(area) <= 100:
        errors.append("Please enter the area / ward (2 to 100 characters).")
    if contact and not (EMAIL_RE.match(contact) or PHONE_RE.match(contact)):
        errors.append("Contact must be a valid email address or a 10-digit phone number.")
    return errors


def days_open(created_at: str) -> float:
    created = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    return (datetime.now() - created).total_seconds() / 86400


# ------------------------------------------------------------------ pages ---
def page_submit() -> None:
    st.header("Submit a Complaint")
    with st.form("complaint_form", clear_on_submit=True):
        text = st.text_area("Complaint description *", height=150, max_chars=2000)
        area = st.text_input("Area / Ward *", max_chars=100)
        contact = st.text_input("Contact (optional): email or 10-digit phone number")
        submitted = st.form_submit_button("Submit complaint")

    if not submitted:
        return
    text, area, contact = text.strip(), area.strip(), contact.strip()
    errors = validate_submission(text, area, contact)
    if errors:
        for e in errors:
            st.error(e)
        return

    category = classifier.predict_category(text)
    result = score_complaint(text, category, area)
    code = db.insert_complaint(text, area, contact, category, result["score"], result["label"])
    st.success(f"Complaint registered. Your complaint ID is **{code}**. Keep it to track the status.")
    c1, c2 = st.columns(2)
    c1.metric("Assigned category", category)
    c2.metric("Assigned priority", result["label"])


def page_track() -> None:
    st.header("Track a Complaint")
    code = st.text_input("Complaint ID (for example GRV-1A2B3C4D)").strip().upper()
    if not code:
        return
    complaint = db.get_complaint(code)
    if complaint is None:
        st.error("No complaint found with this ID.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Status", complaint["status"])
    c2.metric("Category", complaint["category"])
    c3.metric("Priority", complaint["priority_label"])
    st.write(f"**Submitted on:** {complaint['created_at']}")
    st.write(f"**Area / Ward:** {complaint['area']}")
    st.write(f"**Complaint:** {complaint['text']}")
    st.subheader("Status history")
    st.dataframe(db.get_status_history(code), hide_index=True)


def login_form() -> None:
    st.info("Administrator login required.")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Log in"):
            if db.verify_admin(username.strip(), password):
                st.session_state["admin"] = username.strip()
                st.rerun()
            else:
                st.error("Invalid username or password.")


def page_dashboard() -> None:
    st.header("Analytics Dashboard")
    first, last = db.date_range()
    if first is None:
        st.info("No complaints in the database yet.")
        return
    first, last = date.fromisoformat(first), date.fromisoformat(last)
    c1, c2 = st.columns(2)
    date_from = c1.date_input("From", first, min_value=first, max_value=last)
    date_to = c2.date_input("To", last, min_value=first, max_value=last)
    if date_from > date_to:
        st.error("'From' must not be after 'To'.")
        return

    start = time.perf_counter()
    data = db.dashboard_data(str(date_from), str(date_to))
    elapsed = time.perf_counter() - start

    total = int(data["status"]["complaints"].sum())
    if total == 0:
        st.info("No complaints in the selected period.")
        return
    status_counts = dict(zip(data["status"]["status"], data["status"]["complaints"]))
    m = st.columns(4)
    m[0].metric("Total complaints", f"{total:,}")
    m[1].metric("Open", f"{status_counts.get('Open', 0):,}")
    m[2].metric("In progress", f"{status_counts.get('In Progress', 0):,}")
    m[3].metric("Resolved", f"{status_counts.get('Resolved', 0):,}")
    st.caption(f"Dashboard queries ran in {elapsed:.3f} seconds on {total:,} records.")

    st.subheader("1. Complaint volume trend")
    st.plotly_chart(px.line(data["volume"], x="day", y="complaints", markers=True))

    left, right = st.columns(2)
    with left:
        st.subheader("2. Category mix")
        st.plotly_chart(px.bar(data["category"], x="complaints", y="category", orientation="h"))
    with right:
        st.subheader("3. Priority mix")
        st.plotly_chart(px.pie(
            data["priority"], names="priority", values="complaints", color="priority",
            color_discrete_map=PRIORITY_COLOURS,
            category_orders={"priority": config.PRIORITY_LEVELS}))

    left, right = st.columns(2)
    with left:
        st.subheader("4. Area-wise complaints (top 15)")
        st.plotly_chart(px.bar(data["area"], x="area", y="complaints"))
    with right:
        st.subheader("5. Status and resolution time")
        st.plotly_chart(px.bar(data["status"], x="status", y="complaints"))
    st.write("Average resolution time of resolved complaints, by category (hours):")
    st.dataframe(data["resolution"], hide_index=True)


def page_admin() -> None:
    admin = st.session_state["admin"]
    st.header("Administrator Monitoring Console")

    if st.button("Update ageing score of open complaints"):
        st.success(f"Priority recalculated for {refresh_ageing()} open complaints.")

    st.subheader("Complaint queue (sorted by priority)")
    any_ = "All"
    f = st.columns(5)
    status = f[0].selectbox("Status", [any_] + config.STATUSES)
    category = f[1].selectbox("Category", [any_] + config.CATEGORIES)
    priority = f[2].selectbox("Priority", [any_] + config.PRIORITY_LEVELS[::-1])
    area = f[3].selectbox("Area", [any_] + db.list_areas())
    search = f[4].text_input("Search text or ID").strip()

    queue = db.fetch_complaints(
        status=None if status == any_ else status,
        category=None if category == any_ else category,
        priority=None if priority == any_ else priority,
        area=None if area == any_ else area,
        search=search or None,
    )
    columns = ["complaint_code", "priority_label", "priority_score", "status", "category",
               "area", "text", "created_at", "resolved_at"]
    st.write(f"{len(queue):,} complaints match the filters (first 500 shown).")
    st.dataframe(queue[columns].head(500), hide_index=True)
    st.download_button("Export filtered complaints as CSV",
                       queue.drop(columns=["id"]).to_csv(index=False).encode("utf-8"),
                       file_name="complaints_export.csv", mime="text/csv")

    st.subheader("Update a complaint")
    code = st.text_input("Complaint ID to update").strip().upper()
    if not code:
        return
    complaint = db.get_complaint(code)
    if complaint is None:
        st.error("No complaint found with this ID.")
        return

    st.write(f"**Complaint:** {complaint['text']}")
    st.write(f"**Area:** {complaint['area']} | **Contact:** {complaint['contact'] or 'not given'} "
             f"| **Submitted:** {complaint['created_at']}")
    age = 0.0 if complaint["status"] == "Resolved" else days_open(complaint["created_at"])
    parts = score_complaint(complaint["text"], complaint["category"], complaint["area"], age)
    st.caption(
        "Rule-based score: "
        + " + ".join(f"{config.WEIGHTS[k]} x {v:.2f} ({k})" for k, v in parts["components"].items())
        + f" = {parts['score']} -> {parts['label']}"
        + (" | priority was manually overridden" if complaint["priority_overridden"] else ""))

    with st.form("update_form"):
        c = st.columns(3)
        new_status = c[0].selectbox("Status", config.STATUSES,
                                    index=config.STATUSES.index(complaint["status"]))
        new_category = c[1].selectbox("Category (manual override)", config.CATEGORIES,
                                      index=config.CATEGORIES.index(complaint["category"]))
        new_priority = c[2].selectbox("Priority (manual override)", config.PRIORITY_LEVELS,
                                      index=config.PRIORITY_LEVELS.index(complaint["priority_label"]))
        save = st.form_submit_button("Save changes")
    if save:
        db.update_status(code, new_status, admin)
        if new_category != complaint["category"]:
            db.override_category(code, new_category, admin)
            # a new category changes the severity, so the rule-based priority is recalculated
            if not complaint["priority_overridden"] and new_priority == complaint["priority_label"]:
                r = score_complaint(complaint["text"], new_category, complaint["area"], age)
                db.set_priority(code, r["score"], r["label"])
        if new_priority != complaint["priority_label"]:
            db.override_priority(code, new_priority, admin)
        st.success("Changes saved.")
        st.rerun()

    left, right = st.columns(2)
    left.write("Status history")
    left.dataframe(db.get_status_history(code), hide_index=True)
    right.write("Manual override log")
    right.dataframe(db.get_override_log(code), hide_index=True)


def refresh_ageing() -> int:
    """Recalculate the priority of unresolved complaints so that ageing (St) is included."""
    updates = []
    for status in ("Open", "In Progress"):
        for row in db.fetch_complaints(status=status).itertuples():
            if row.priority_overridden:
                continue
            r = score_complaint(row.text, row.category, row.area, days_open(row.created_at))
            updates.append((r["score"], r["label"], row.id))
    with db.get_conn() as conn:
        conn.executemany("UPDATE complaints SET priority_score = ?, priority_label = ? WHERE id = ?", updates)
    return len(updates)


# ------------------------------------------------------------------- main ---
def main() -> None:
    if not config.DB_PATH.exists() or not classifier.model_available():
        st.error("The system is not set up yet. Run the setup steps in the README "
                 "(prepare_data.py, train_model.py, setup_database.py) and restart the app.")
        st.stop()

    st.sidebar.title("Public Grievance System")
    page = st.sidebar.radio("Go to", ["Submit Complaint", "Track Complaint",
                                      "Analytics Dashboard", "Admin Console"])
    if "admin" in st.session_state:
        st.sidebar.write(f"Logged in as **{st.session_state['admin']}**")
        if st.sidebar.button("Log out"):
            del st.session_state["admin"]
            st.rerun()
    st.sidebar.caption(f"Classifier: {classifier.model_name()}")

    if page == "Submit Complaint":
        page_submit()
    elif page == "Track Complaint":
        page_track()
    elif "admin" not in st.session_state:
        login_form()
    elif page == "Analytics Dashboard":
        page_dashboard()
    else:
        page_admin()


main()
