import os
from datetime import date, datetime

import altair as alt
import pandas as pd
import plotly.graph_objects as go
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

# field, English label (teacher form), Vietnamese label (parent portal), color
RATING_CRITERIA = [
    ("pronunciation_rating", "Pronunciation", "Phát âm", "#273f73"),
    ("confidence_rating", "Confidence", "Sự tự tin", "#6d83b3"),
    ("participation_rating", "Participation", "Tham gia phát biểu", "#e8b923"),
    ("homework_rating", "Homework quality", "Chất lượng bài tập", "#8a94a6"),
    ("listening_rating", "Listening", "Nghe", "#3f6fae"),
    ("reading_rating", "Reading", "Đọc", "#4caf7d"),
    ("writing_rating", "Writing", "Viết", "#c96b3c"),
    ("grammar_rating", "Grammar accuracy", "Độ chính xác ngữ pháp", "#7a5ea8"),
    ("vocabulary_rating", "Vocabulary", "Vốn từ vựng", "#2f9199"),
]
# Radar chart axes: NÓI / NGHE / ĐỌC / VIẾT, mapped from existing rating fields.
RADAR_AXES = [
    ("pronunciation_rating", "NÓI"),
    ("listening_rating", "NGHE"),
    ("reading_rating", "ĐỌC"),
    ("writing_rating", "VIẾT"),
]

# Competency gauges, shown as a completion percentage (rating / 5).
GAUGE_METRICS = [
    ("grammar_rating", "Độ chính xác ngữ pháp", "#7a5ea8"),
    ("vocabulary_rating", "Vốn từ vựng", "#2f9199"),
    ("homework_rating", "Tỷ lệ hoàn thành bài tập", "#e8b923"),
]

VI_TEXT = {
    "hero_subtitle_sep": " · ",
    "skill_balance": "Cân bằng kỹ năng",
    "learning_trend": "Xu hướng học tập",
    "chart_avg_score": "Điểm trung bình",
    "competency_gauges": "Chỉ số năng lực",
    "latest_snapshot": "Đánh giá gần nhất",
    "latest_snapshot_sub": "Nhận xét mới nhất từ giáo viên",
    "as_of": "Ngày {date}",
    "no_ratings": "Chưa có đánh giá nào.",
    "chart_date": "Ngày",
    "quest_log": "Nhật Ký Thử Thách",
    "no_objectives": "Chưa có nhiệm vụ nào.",
    "quests_completed": "{completed}/{total} nhiệm vụ hoàn thành",
    "milestones": "Cột mốc đạt được",
    "no_milestones": "Chưa có cột mốc nào.",
    "invalid_link": "Đường liên kết không hợp lệ. Vui lòng kiểm tra lại đường liên kết mà giáo viên đã gửi cho bạn.",
    "not_enough_data": "Cần thêm dữ liệu đánh giá để hiển thị biểu đồ này.",
    "streak_active": "🔥 Chuỗi chuyên cần: {n} tuần liên tiếp!",
    "streak_inactive": "🔥 Chưa có chuỗi chuyên cần — hãy bắt đầu với bài tập tiếp theo!",
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

div[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: 14px;
  box-shadow: 0 3px 14px rgba(39, 63, 115, 0.08);
}
div[data-testid="stVerticalBlockBorderWrapper"] h4 {
  color: #273f73;
  margin-top: 0;
}

.quest-active {
  padding: 0.3rem 0;
  color: #1F2937;
}
.quest-completed {
  padding: 0.3rem 0;
  color: #b8860b;
}
.quest-completed .quest-title {
  text-decoration: line-through;
  opacity: 0.75;
  text-shadow: 0 0 6px rgba(255, 222, 89, 0.5);
}

.streak-badge {
  display: inline-block;
  padding: 0.4rem 1.1rem;
  border-radius: 999px;
  font-weight: 600;
  margin-bottom: 1.25rem;
}
.streak-badge.active {
  background: linear-gradient(135deg, #ffde59, #ffb020);
  color: #273f73;
  animation: pulseGlow 2s ease-in-out infinite;
}
.streak-badge.inactive {
  background: #eef1f8;
  color: #8a94a6;
}
@keyframes pulseGlow {
  0%, 100% { box-shadow: 0 2px 10px rgba(255, 176, 32, 0.35); }
  50% { box-shadow: 0 2px 18px rgba(255, 176, 32, 0.65); }
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


def build_radar_chart(ratings: list) -> go.Figure:
    df = pd.DataFrame(ratings)
    values, labels = [], []
    for field, axis_label in RADAR_AXES:
        avg = df[field].dropna().mean() if field in df.columns else None
        values.append(round(avg, 2) if pd.notna(avg) else 0)
        labels.append(axis_label)
    values.append(values[0])
    labels.append(labels[0])

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=labels,
            fill="toself",
            line=dict(color="#273f73", width=2),
            fillcolor="rgba(39, 63, 115, 0.25)",
            marker=dict(color="#273f73", size=6),
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 5], tickvals=[1, 2, 3, 4, 5])),
        showlegend=False,
        margin=dict(l=40, r=40, t=30, b=30),
        height=320,
    )
    return fig


def build_gauge_figure(field: str, label: str, color: str, df: pd.DataFrame) -> go.Figure:
    avg = df[field].dropna().mean() if field in df.columns else None
    pct = round(avg / 5 * 100) if pd.notna(avg) else 0
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=pct,
            number={"suffix": "%", "font": {"size": 26}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": color},
                "bgcolor": "#eef1f8",
                "borderwidth": 0,
            },
            title={"text": label, "font": {"size": 13}},
        )
    )
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=45, b=10))
    return fig


def build_trend_chart(ratings: list) -> alt.Chart:
    df = pd.DataFrame(ratings)
    df["rating_date"] = pd.to_datetime(df["rating_date"])
    value_cols = [field for field, _, _, _ in RATING_CRITERIA if field in df.columns]
    df["avg_score"] = df[value_cols].mean(axis=1, skipna=True)
    df = df.dropna(subset=["avg_score"]).sort_values("rating_date")

    area = (
        alt.Chart(df)
        .mark_area(interpolate="monotone", line={"color": "#273f73"}, color="#a9bad9", opacity=0.4)
        .encode(
            x=alt.X("rating_date:T", title=VI_TEXT["chart_date"]),
            y=alt.Y("avg_score:Q", title=VI_TEXT["chart_avg_score"], scale=alt.Scale(domain=[1, 5])),
            tooltip=["rating_date:T", alt.Tooltip("avg_score:Q", format=".1f")],
        )
    )
    points = (
        alt.Chart(df)
        .mark_point(color="#273f73", filled=True, size=50)
        .encode(x="rating_date:T", y="avg_score:Q")
    )
    return (area + points).properties(height=280)


def compute_streak(ratings: list) -> tuple:
    """Consecutive-calendar-weeks streak based on Homework Quality >= 4 stars.

    Computed fresh from history every time rather than stored as a mutable
    counter, so it can never drift if a teacher edits or backfills a rating.
    """
    qualifying_weeks = set()
    for r in ratings:
        homework = r.get("homework_rating")
        if homework is not None and homework >= 4:
            d = datetime.strptime(r["rating_date"], "%Y-%m-%d").date()
            iso_year, iso_week, _ = d.isocalendar()
            qualifying_weeks.add((iso_year, iso_week))

    if not qualifying_weeks:
        return 0, 0

    week_mondays = sorted(date.fromisocalendar(y, w, 1) for y, w in qualifying_weeks)

    longest = current = 1
    for i in range(1, len(week_mondays)):
        gap_weeks = (week_mondays[i] - week_mondays[i - 1]).days // 7
        current = current + 1 if gap_weeks == 1 else 1
        longest = max(longest, current)

    return current, longest


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
    objectives = data.get("objectives") or []
    milestones = data.get("milestones") or []
    ratings_df = pd.DataFrame(ratings) if ratings else pd.DataFrame()

    current_streak, _longest_streak = compute_streak(ratings)
    if current_streak > 0:
        st.markdown(
            f'<div class="streak-badge active">{VI_TEXT["streak_active"].format(n=current_streak)}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f'<div class="streak-badge inactive">{VI_TEXT["streak_inactive"]}</div>', unsafe_allow_html=True)

    # Row 1: skill balance radar + learning trend
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown(f"#### 📊 {VI_TEXT['skill_balance']}")
            if ratings:
                st.plotly_chart(build_radar_chart(ratings), use_container_width=True)
            else:
                st.write(VI_TEXT["not_enough_data"])
    with col2:
        with st.container(border=True):
            st.markdown(f"#### 📈 {VI_TEXT['learning_trend']}")
            if ratings:
                st.altair_chart(build_trend_chart(ratings), use_container_width=True)
            else:
                st.write(VI_TEXT["not_enough_data"])

    # Row 2: competency gauges
    with st.container(border=True):
        st.markdown(f"#### 🎯 {VI_TEXT['competency_gauges']}")
        if ratings:
            gauge_cols = st.columns(len(GAUGE_METRICS))
            for col, (field, label, color) in zip(gauge_cols, GAUGE_METRICS):
                with col:
                    st.plotly_chart(build_gauge_figure(field, label, color, ratings_df), use_container_width=True)
        else:
            st.write(VI_TEXT["not_enough_data"])

    # Row 3: latest snapshot + objectives/milestones
    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            st.markdown(f"#### 📝 {VI_TEXT['latest_snapshot']}")
            st.caption(VI_TEXT["latest_snapshot_sub"])
            if not ratings:
                st.write(VI_TEXT["no_ratings"])
            else:
                latest = ratings[-1]
                st.write(f"**{VI_TEXT['as_of'].format(date=format_date_vi(latest['rating_date']))}**")
                for field, _en, vi_label, _color in RATING_CRITERIA:
                    value = latest.get(field)
                    if value:
                        st.markdown(f"{vi_label}: {_stars_html(value, total=5)}", unsafe_allow_html=True)
                if latest.get("notes"):
                    st.caption(latest["notes"])

    with col4:
        with st.container(border=True):
            st.markdown(f"#### ⚔️ {VI_TEXT['quest_log']}")

            if not objectives:
                st.write(VI_TEXT["no_objectives"])
            else:
                completed_count = sum(1 for o in objectives if o["status"] == "mastered")
                st.progress(
                    completed_count / len(objectives),
                    text=VI_TEXT["quests_completed"].format(completed=completed_count, total=len(objectives)),
                )
                for o in objectives:
                    if o["status"] == "mastered":
                        st.markdown(
                            f'<div class="quest-completed">🏆 <span class="quest-title">{o["title"]}</span></div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        tag = " <em>(đang thực hiện)</em>" if o["status"] == "in_progress" else ""
                        st.markdown(
                            f'<div class="quest-active">🛡️ {o["title"]}{tag}</div>', unsafe_allow_html=True
                        )

            st.markdown(f"**{VI_TEXT['milestones']}**")
            if not milestones:
                st.write(VI_TEXT["no_milestones"])
            else:
                for m in milestones:
                    st.write(f"🏅 {format_date_vi(m['achieved_at'])} — {m['title']}")


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

            with st.form(f"edit_student_{s['id']}"):
                col1, col2, col3 = st.columns(3)
                current_class_name = s["classes"]["name"] if s.get("classes") else list(class_options.keys())[0]
                new_class_name = col1.selectbox(
                    "Class",
                    list(class_options.keys()),
                    index=list(class_options.keys()).index(current_class_name)
                    if current_class_name in class_options
                    else 0,
                    key=f"class_{s['id']}",
                )
                new_name = col2.text_input("Student name", value=s["name"], key=f"name_{s['id']}")
                new_parent_contact = col3.text_input(
                    "Parent contact (email/phone)", value=s.get("parent_contact") or "", key=f"contact_{s['id']}"
                )
                confirm_delete = st.checkbox(
                    "Yes, permanently delete this student and all their ratings/milestones/progress",
                    key=f"confirm_delete_{s['id']}",
                )
                save_col, delete_col = st.columns(2)
                save = save_col.form_submit_button("Save changes")
                delete = delete_col.form_submit_button("Delete student", type="secondary")

            if save and new_name:
                client.table("students").update(
                    {
                        "class_id": class_options[new_class_name],
                        "name": new_name,
                        "parent_contact": new_parent_contact or None,
                    }
                ).eq("id", s["id"]).execute()
                st.rerun()

            if delete and not confirm_delete:
                st.warning("Check the confirmation box above before deleting.")

            if delete and confirm_delete:
                client.table("milestones").delete().eq("student_id", s["id"]).execute()
                client.table("student_ratings").delete().eq("student_id", s["id"]).execute()
                client.table("student_objective_status").delete().eq("student_id", s["id"]).execute()
                client.table("students").delete().eq("id", s["id"]).execute()
                st.rerun()


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

        st.caption("Core")
        core_criteria = RATING_CRITERIA[:4]
        core_cols = st.columns(len(core_criteria))
        for col, (field, label, _vi, _color) in zip(core_cols, core_criteria):
            with col:
                st.write(label)
                choice = st.feedback("stars", key=f"rating_{field}")
                rating_values[field] = (choice + 1) if choice is not None else None

        st.caption("Language skills")
        skill_criteria = RATING_CRITERIA[4:]
        skill_cols = st.columns(len(skill_criteria))
        for col, (field, label, _vi, _color) in zip(skill_cols, skill_criteria):
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
