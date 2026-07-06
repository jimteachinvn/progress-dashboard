import os
from datetime import date, datetime

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


def get_setting(key: str) -> str:
    try:
        if key in st.secrets:
            return st.secrets[key]
    except st.errors.StreamlitSecretNotFoundError:
        pass
    return os.environ.get(key)


SUPABASE_URL = get_setting("SUPABASE_URL")
SUPABASE_KEY = get_setting("SUPABASE_KEY")

STATUS_FILLED = {"not_started": 0, "in_progress": 2, "mastered": 3}

RATING_CRITERIA = [
    ("pronunciation_rating", "Pronunciation", "#273f73"),
    ("confidence_rating", "Confidence", "#6d83b3"),
    ("participation_rating", "Participation", "#e8b923"),
    ("homework_rating", "Homework quality", "#8a94a6"),
]

# Vietnamese labels for the same criteria, used only in the parent-facing portal.
VI_CRITERION_LABELS = {
    "pronunciation_rating": "Phát âm",
    "confidence_rating": "Sự tự tin",
    "participation_rating": "Tham gia phát biểu",
    "homework_rating": "Chất lượng bài tập",
}

VI_TEXT = {
    "hero_subtitle_sep": " · ",
    "latest_snapshot": "Đánh giá gần nhất",
    "as_of": "Tính đến ngày {date}",
    "no_ratings": "Chưa có đánh giá nào.",
    "progress_over_time": "Tiến độ theo thời gian",
    "chart_date": "Ngày",
    "chart_stars": "Số sao",
    "chart_criterion": "Tiêu chí",
    "full_history": "Xem toàn bộ lịch sử đánh giá",
    "learning_objectives": "Mục tiêu học tập",
    "no_objectives": "Chưa có mục tiêu nào.",
    "objectives_mastered": "{mastered}/{total} mục tiêu đã hoàn thành",
    "general_category": "Chung",
    "milestones": "Cột mốc đạt được",
    "no_milestones": "Chưa có cột mốc nào.",
    "invalid_link": "Đường liên kết không hợp lệ. Vui lòng kiểm tra lại đường liên kết mà giáo viên đã gửi cho bạn.",
}


def format_date_vi(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return date_str


def _stars_plain(filled: int, total: int = 3) -> str:
    return ("★ " * filled + "☆ " * (total - filled)).strip()


def _stars_html(filled: int, total: int = 3) -> str:
    filled = filled or 0
    filled_part = f'<span class="star-filled">{"★" * filled}</span>' if filled else ""
    empty_part = f'<span class="star-empty">{"☆" * (total - filled)}</span>' if total - filled else ""
    return f'<span class="star-rating">{filled_part}{empty_part}</span>'


STATUS_STARS = {k: _stars_plain(v) for k, v in STATUS_FILLED.items()}
STATUS_STARS_HTML = {k: _stars_html(v) for k, v in STATUS_FILLED.items()}

st.set_page_config(page_title="ESL Progress Dashboard", page_icon="📘", layout="wide")

CUSTOM_CSS = """
<style>
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.main .block-container {
  animation: fadeInUp 0.35s ease-out;
  max-width: 1100px;
}

.esl-hero {
  background: linear-gradient(135deg, #273f73 0%, #32508f 100%);
  color: #ffffff;
  padding: 1.5rem 1.75rem;
  border-radius: 14px;
  margin-bottom: 1.5rem;
  box-shadow: 0 6px 20px rgba(39, 63, 115, 0.18);
}
.esl-hero h1 {
  color: #ffffff;
  margin: 0;
  font-size: 1.9rem;
}
.esl-hero p {
  color: #ffde59;
  margin: 0.25rem 0 0 0;
  font-size: 1rem;
}

div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
  background: #273f73;
  color: #ffffff;
  border: 1px solid #273f73;
  border-radius: 8px;
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}
div.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
  background: #32508f;
  color: #ffde59;
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(39, 63, 115, 0.3);
}

.star-rating { letter-spacing: 2px; font-size: 1.05rem; }
.star-filled { color: #ffde59; text-shadow: 0 0 1px rgba(39, 63, 115, 0.4); }
.star-empty { color: #c9ced9; }

div[data-testid="stExpander"] {
  border-radius: 10px;
  border: 1px solid #e3e7f1;
}

@media (max-width: 640px) {
  .main .block-container { padding-left: 1rem; padding-right: 1rem; }
  .esl-hero { padding: 1.1rem 1.25rem; }
  .esl-hero h1 { font-size: 1.5rem; }
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_hero(title: str, subtitle: str = None):
    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(f'<div class="esl-hero"><h1>{title}</h1>{subtitle_html}</div>', unsafe_allow_html=True)


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
        st.error(VI_TEXT["invalid_link"])
        return

    student = data["student"]
    subtitle = student.get("class_name")
    if subtitle and student.get("class_level"):
        subtitle = f"{subtitle}{VI_TEXT['hero_subtitle_sep']}{student['class_level']}"
    render_hero(f"Tiến độ học tập của {student['name']}", subtitle)

    ratings = data.get("ratings") or []

    st.subheader(VI_TEXT["latest_snapshot"])
    if not ratings:
        st.write(VI_TEXT["no_ratings"])
    else:
        latest = ratings[-1]
        st.caption(VI_TEXT["as_of"].format(date=format_date_vi(latest["rating_date"])))
        cols = st.columns(len(RATING_CRITERIA))
        for col, (field, _label, _color) in zip(cols, RATING_CRITERIA):
            value = latest.get(field)
            stars = _stars_html(value, total=5) if value else "—"
            with col:
                st.markdown(f"**{VI_CRITERION_LABELS[field]}**<br>{stars}", unsafe_allow_html=True)

    if len(ratings) >= 2:
        st.subheader(VI_TEXT["progress_over_time"])
        df = pd.DataFrame(ratings)
        df["rating_date"] = pd.to_datetime(df["rating_date"])
        value_cols = [field for field, _, _ in RATING_CRITERIA]
        color_map = {VI_CRITERION_LABELS[field]: color for field, _, color in RATING_CRITERIA}

        long_df = df.melt(id_vars="rating_date", value_vars=value_cols, var_name="criterion", value_name="stars")
        long_df["criterion"] = long_df["criterion"].map(VI_CRITERION_LABELS)
        long_df = long_df.dropna(subset=["stars"])

        chart = (
            alt.Chart(long_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("rating_date:T", title=VI_TEXT["chart_date"]),
                y=alt.Y("stars:Q", title=VI_TEXT["chart_stars"], scale=alt.Scale(domain=[1, 5])),
                color=alt.Color(
                    "criterion:N",
                    title=VI_TEXT["chart_criterion"],
                    scale=alt.Scale(domain=list(color_map.keys()), range=list(color_map.values())),
                ),
                tooltip=["rating_date:T", "criterion:N", "stars:Q"],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)

    if ratings:
        with st.expander(VI_TEXT["full_history"]):
            for r in reversed(ratings):
                parts = [
                    f"{VI_CRITERION_LABELS[field]}: {_stars_html(r.get(field), total=5)}"
                    for field, _, _ in RATING_CRITERIA
                    if r.get(field)
                ]
                st.markdown(
                    f"**{format_date_vi(r['rating_date'])}** — " + "&nbsp;&nbsp;&nbsp;".join(parts),
                    unsafe_allow_html=True,
                )
                if r.get("notes"):
                    st.caption(r["notes"])

    st.divider()
    st.subheader(VI_TEXT["learning_objectives"])
    objectives = data.get("objectives") or []
    if not objectives:
        st.write(VI_TEXT["no_objectives"])
    else:
        mastered_count = sum(1 for o in objectives if o["status"] == "mastered")
        st.progress(
            mastered_count / len(objectives),
            text=VI_TEXT["objectives_mastered"].format(mastered=mastered_count, total=len(objectives)),
        )

        by_category = {}
        for o in objectives:
            by_category.setdefault(o.get("category") or VI_TEXT["general_category"], []).append(o)
        for category, items in by_category.items():
            st.markdown(f"**{category}**")
            for o in items:
                stars = STATUS_STARS_HTML.get(o["status"], STATUS_STARS_HTML["not_started"])
                st.markdown(f"{o['title']} — {stars}", unsafe_allow_html=True)
                if o.get("description"):
                    st.caption(o["description"])

    st.divider()
    st.subheader(VI_TEXT["milestones"])
    milestones = data.get("milestones") or []
    if not milestones:
        st.write(VI_TEXT["no_milestones"])
    else:
        for m in milestones:
            st.write(f"🏆 **{format_date_vi(m['achieved_at'])}** — {m['title']}")


# ---------------------------------------------------------------------------
# Teacher dashboard (Supabase Auth email/password login required)
# ---------------------------------------------------------------------------

def render_login():
    render_hero("Teacher login")
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
    if not objectives:
        st.write("No objectives for this class yet.")
        return

    for o in objectives:
        with st.expander(f"{o.get('order_index', 0)}. {o.get('category') or '—'} — {o['title']}"):
            with st.form(f"edit_objective_{o['id']}"):
                col1, col2 = st.columns(2)
                new_category = col1.text_input("Category", value=o.get("category") or "", key=f"cat_{o['id']}")
                new_title = col2.text_input("Objective title", value=o["title"], key=f"title_{o['id']}")
                new_description = st.text_area(
                    "Description (optional)", value=o.get("description") or "", key=f"desc_{o['id']}"
                )
                new_order = st.number_input(
                    "Order", min_value=0, step=1, value=o.get("order_index") or 0, key=f"order_{o['id']}"
                )
                save_col, delete_col = st.columns(2)
                save = save_col.form_submit_button("Save changes")
                delete = delete_col.form_submit_button("Delete objective", type="secondary")

            if save and new_title:
                client.table("objectives").update(
                    {
                        "category": new_category or None,
                        "title": new_title,
                        "description": new_description or None,
                        "order_index": int(new_order),
                    }
                ).eq("id", o["id"]).execute()
                st.rerun()

            if delete:
                client.table("student_objective_status").delete().eq("objective_id", o["id"]).execute()
                client.table("objectives").delete().eq("id", o["id"]).execute()
                st.rerun()


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

    st.markdown("#### Add a progress check-in")
    with st.form("rating_form", clear_on_submit=True):
        rating_date = st.date_input("Date", value=date.today())
        rating_values = {}
        cols = st.columns(len(RATING_CRITERIA))
        for col, (field, label, _color) in zip(cols, RATING_CRITERIA):
            with col:
                st.write(label)
                choice = st.feedback("stars", key=f"rating_{field}")
                rating_values[field] = (choice + 1) if choice is not None else None
        notes = st.text_area("Notes", key="rating_notes")
        if st.form_submit_button("Add check-in"):
            client.table("student_ratings").insert(
                {
                    "student_id": student["id"],
                    "rating_date": rating_date.isoformat(),
                    "notes": notes or None,
                    **rating_values,
                }
            ).execute()
            st.success("Check-in added.")

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

    render_hero("ESL Progress Dashboard")

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
