import os
from datetime import date

import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

STATUS_STARS = {
    "not_started": "☆ ☆ ☆",
    "in_progress": "★ ★ ☆",
    "mastered": "★ ★ ★",
}
RATING_STARS = {
    "needs_work": "★ ☆ ☆",
    "developing": "★ ★ ☆",
    "strong": "★ ★ ★",
}

st.set_page_config(page_title="ESL Progress Dashboard", page_icon="📘", layout="wide")


@st.cache_resource
def get_public_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------------------------------------------------------
# Parent portal (no login, read-only, reached via ?token=...)
# ---------------------------------------------------------------------------

def render_parent_portal(token: str):
    client = get_public_client()
    res = client.rpc("get_student_portal", {"p_access_token": token}).execute()
    data = res.data

    if not data:
        st.error("This link isn't valid. Please double-check the link your teacher sent you.")
        return

    student = data["student"]
    st.title(f"{student['name']}'s Progress")
    if student.get("class_name"):
        st.caption(f"{student['class_name']}" + (f" · {student['class_level']}" if student.get("class_level") else ""))

    st.divider()
    st.subheader("Learning objectives")
    objectives = data.get("objectives") or []
    if not objectives:
        st.write("No objectives have been added yet.")
    else:
        by_category = {}
        for o in objectives:
            by_category.setdefault(o.get("category") or "General", []).append(o)
        for category, items in by_category.items():
            st.markdown(f"**{category}**")
            for o in items:
                stars = STATUS_STARS.get(o["status"], STATUS_STARS["not_started"])
                st.write(f"{o['title']} — {stars}")
                if o.get("description"):
                    st.caption(o["description"])

    st.divider()
    st.subheader("Speaking ratings")
    ratings = data.get("ratings") or []
    if not ratings:
        st.write("No ratings recorded yet.")
    else:
        for r in ratings:
            pron = RATING_STARS.get(r["pronunciation_rating"], "—")
            conf = RATING_STARS.get(r["confidence_rating"], "—")
            st.write(f"**{r['rating_date']}** — Pronunciation: {pron}   Confidence: {conf}")
            if r.get("notes"):
                st.caption(r["notes"])

    st.divider()
    st.subheader("Milestones")
    milestones = data.get("milestones") or []
    if not milestones:
        st.write("No milestones recorded yet.")
    else:
        for m in milestones:
            st.write(f"🏆 **{m['achieved_at']}** — {m['title']}")


# ---------------------------------------------------------------------------
# Teacher dashboard (Supabase Auth email/password login required)
# ---------------------------------------------------------------------------

def render_login():
    st.title("Teacher login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        try:
            client.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.sb_client = client
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {e}")


def render_classes(client: Client):
    st.subheader("Classes")
    with st.form("new_class_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name = col1.text_input("Class name")
        level = col2.text_input("Level (e.g. A2, B1)")
        if st.form_submit_button("Add class") and name:
            client.table("classes").insert({"name": name, "level": level or None}).execute()
            st.rerun()

    classes = client.table("classes").select("*").order("created_at").execute().data
    if classes:
        st.table([{"Name": c["name"], "Level": c.get("level") or "—"} for c in classes])
    else:
        st.write("No classes yet — add one above.")


def render_students(client: Client):
    st.subheader("Students")
    classes = client.table("classes").select("*").order("created_at").execute().data
    if not classes:
        st.info("Add a class first.")
        return

    class_options = {c["name"]: c["id"] for c in classes}
    with st.form("new_student_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        class_name = col1.selectbox("Class", list(class_options.keys()))
        name = col2.text_input("Student name")
        parent_contact = col3.text_input("Parent contact (email/phone)")
        if st.form_submit_button("Add student") and name:
            client.table("students").insert(
                {"class_id": class_options[class_name], "name": name, "parent_contact": parent_contact or None}
            ).execute()
            st.rerun()

    students = client.table("students").select("*, classes(name)").order("created_at").execute().data
    if not students:
        st.write("No students yet — add one above.")
        return

    base_url = st.text_input(
        "Your app's URL (used to build shareable parent links)",
        value=st.session_state.get("base_url", ""),
        placeholder="https://your-app-name.streamlit.app",
    )
    st.session_state.base_url = base_url

    for s in students:
        with st.expander(f"{s['name']} ({s['classes']['name'] if s.get('classes') else 'no class'})"):
            link = f"{base_url.rstrip('/')}/?token={s['access_token']}" if base_url else f"?token={s['access_token']}"
            st.write("Parent link:")
            st.code(link)


def render_objectives(client: Client):
    st.subheader("Objectives")
    classes = client.table("classes").select("*").order("created_at").execute().data
    if not classes:
        st.info("Add a class first.")
        return

    class_options = {c["name"]: c["id"] for c in classes}
    class_name = st.selectbox("Class", list(class_options.keys()), key="obj_class_select")
    class_id = class_options[class_name]

    with st.form("new_objective_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        category = col1.text_input("Category (e.g. Speaking, Grammar)")
        title = col2.text_input("Objective title")
        description = st.text_area("Description (optional)")
        order_index = st.number_input("Order", min_value=0, step=1, value=0)
        if st.form_submit_button("Add objective") and title:
            client.table("objectives").insert(
                {
                    "class_id": class_id,
                    "category": category or None,
                    "title": title,
                    "description": description or None,
                    "order_index": int(order_index),
                }
            ).execute()
            st.rerun()

    objectives = (
        client.table("objectives")
        .select("*")
        .eq("class_id", class_id)
        .order("order_index")
        .execute()
        .data
    )
    if objectives:
        st.table(
            [
                {"Order": o.get("order_index"), "Category": o.get("category") or "—", "Title": o["title"]}
                for o in objectives
            ]
        )
    else:
        st.write("No objectives for this class yet.")


def render_track_progress(client: Client):
    st.subheader("Track progress")
    students = client.table("students").select("*, classes(id, name)").order("name").execute().data
    if not students:
        st.info("Add a student first.")
        return

    student_options = {s["name"]: s for s in students}
    student_name = st.selectbox("Student", list(student_options.keys()))
    student = student_options[student_name]
    class_id = student["classes"]["id"] if student.get("classes") else None

    st.markdown("#### Objective status")
    objectives = (
        client.table("objectives").select("*").eq("class_id", class_id).order("order_index").execute().data
        if class_id
        else []
    )
    existing_status = {
        row["objective_id"]: row
        for row in client.table("student_objective_status")
        .select("*")
        .eq("student_id", student["id"])
        .execute()
        .data
    }

    if not objectives:
        st.write("This student's class has no objectives yet.")
    else:
        for o in objectives:
            current = existing_status.get(o["id"], {})
            col1, col2 = st.columns([1, 2])
            with col1:
                status = st.radio(
                    o["title"],
                    list(STATUS_STARS.keys()),
                    format_func=lambda s: STATUS_STARS[s],
                    index=list(STATUS_STARS.keys()).index(current.get("status", "not_started")),
                    horizontal=True,
                    key=f"status_{o['id']}",
                )
            with col2:
                notes = st.text_input("Notes", value=current.get("notes") or "", key=f"notes_{o['id']}")
            if st.button("Save", key=f"save_{o['id']}"):
                client.table("student_objective_status").upsert(
                    {
                        "student_id": student["id"],
                        "objective_id": o["id"],
                        "status": status,
                        "notes": notes or None,
                    },
                    on_conflict="student_id,objective_id",
                ).execute()
                st.success("Saved.")

    st.markdown("#### Add a speaking rating")
    with st.form("rating_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        rating_date = col1.date_input("Date", value=date.today())
        pronunciation = col2.radio(
            "Pronunciation", list(RATING_STARS.keys()), format_func=lambda s: RATING_STARS[s], horizontal=True
        )
        confidence = col3.radio(
            "Confidence", list(RATING_STARS.keys()), format_func=lambda s: RATING_STARS[s], horizontal=True
        )
        notes = st.text_area("Notes", key="rating_notes")
        if st.form_submit_button("Add rating"):
            client.table("student_ratings").insert(
                {
                    "student_id": student["id"],
                    "rating_date": rating_date.isoformat(),
                    "pronunciation_rating": pronunciation,
                    "confidence_rating": confidence,
                    "notes": notes or None,
                }
            ).execute()
            st.success("Rating added.")

    st.markdown("#### Add a milestone")
    with st.form("milestone_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        title = col1.text_input("Milestone")
        achieved_at = col2.date_input("Achieved on", value=date.today(), key="milestone_date")
        if st.form_submit_button("Add milestone") and title:
            client.table("milestones").insert(
                {"student_id": student["id"], "title": title, "achieved_at": achieved_at.isoformat()}
            ).execute()
            st.success("Milestone added.")


def render_teacher_app():
    client: Client = st.session_state.sb_client

    with st.sidebar:
        st.write(f"Logged in as **{client.auth.get_user().user.email}**")
        if st.button("Log out"):
            client.auth.sign_out()
            del st.session_state.sb_client
            st.rerun()
        st.divider()
        page = st.radio("Section", ["Classes", "Students", "Objectives", "Track progress"])

    st.title("ESL Progress Dashboard")

    if page == "Classes":
        render_classes(client)
    elif page == "Students":
        render_students(client)
    elif page == "Objectives":
        render_objectives(client)
    elif page == "Track progress":
        render_track_progress(client)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

token = st.query_params.get("token")
if token:
    render_parent_portal(token)
elif "sb_client" in st.session_state:
    render_teacher_app()
else:
    render_login()
