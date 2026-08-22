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

# The six in-class communication criteria this class is actually taught on.
# (field, English label for the teacher form, short Vietnamese label for the
#  radar axis, full Vietnamese description for parents, chart colour)
RATING_CRITERIA = [
    ("fluency_rating", "Fluency & Flow", "Trôi chảy", "Nói trôi chảy, ít ngập ngừng", "#273f73"),
    ("clarity_volume_rating", "Clarity & Volume", "Rõ ràng", "Phát âm rõ & nói đủ nghe", "#3f6fae"),
    ("confidence_willingness_rating", "Confidence & Willingness", "Tự tin", "Tự tin & sẵn sàng phát biểu", "#2f9199"),
    ("interactive_engagement_rating", "Interactive Engagement", "Tương tác", "Tương tác & phối hợp với bạn", "#4caf7d"),
    ("vocabulary_application_rating", "Vocabulary Application", "Từ vựng", "Vận dụng từ vựng đã học", "#e8b923"),
    ("sentence_construction_rating", "Sentence Construction", "Đặt câu", "Đặt câu hoàn chỉnh khi nói", "#7a5ea8"),
]

# Homework is graded and shown to parents, but deliberately sits outside the
# six: it measures work done at home, not in-class communication. It is
# excluded from the radar, the trend line and the streak.
HOMEWORK_FIELD = "homework_rating"
HOMEWORK_EN = "Homework quality"
HOMEWORK_VI = "Chất lượng bài tập về nhà"
HOMEWORK_COLOR = "#e8b923"

VI_TEXT = {
    "hero_subtitle_sep": " · ",
    "skill_balance": "Cân bằng kỹ năng giao tiếp",
    "learning_trend": "Xu hướng học tập",
    "chart_avg_score": "Điểm trung bình",
    "homework_gauge": "Bài tập về nhà",
    "comment_history": "Nhận xét của giáo viên",
    "comment_history_sub": "Nhận xét theo từng buổi học, mới nhất ở trên cùng",
    "latest_label": "Buổi học gần nhất",
    "no_comments": "Chưa có nhận xét nào.",
    "chart_date": "Ngày",
    "per_criterion": "Xem chi tiết từng kỹ năng",
    "milestones": "Cột mốc đạt được",
    "no_milestones": "Chưa có cột mốc nào.",
    "invalid_link": "Đường liên kết không hợp lệ. Vui lòng kiểm tra lại đường liên kết mà giáo viên đã gửi cho bạn.",
    "not_enough_data": "Cần thêm dữ liệu đánh giá để hiển thị biểu đồ này.",
    "not_yet_graded": "chưa đánh giá",
    "streak_active": "🔥 Chuỗi chuyên cần: {n} tuần liên tiếp!",
    "streak_inactive": "🔥 Chưa có chuỗi chuyên cần — hãy bắt đầu từ buổi học tới nhé!",
}


def format_date_vi(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return date_str


def _stars_plain(filled: int, total: int = 5) -> str:
    filled = filled or 0
    return ("★ " * filled + "☆ " * (total - filled)).strip()


def _stars_html(filled: int, total: int = 5) -> str:
    filled = filled or 0
    filled_part = f'<span class="star-filled">{"★" * filled}</span>' if filled else ""
    empty_part = f'<span class="star-empty">{"☆" * (total - filled)}</span>' if total - filled else ""
    return f'<span class="star-rating">{filled_part}{empty_part}</span>'


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

/* --- teacher comment timeline --- */
.session-latest-header {
  font-weight: 700;
  color: #273f73;
  font-size: 1.05rem;
  margin: 0.4rem 0 0.6rem 0;
}
.session-stars {
  margin-bottom: 0.75rem;
}
.session-stars-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
  padding: 0.15rem 0;
  max-width: 460px;
}
.session-stars-label {
  color: #4b5563;
  font-size: 0.92rem;
}
.session-note {
  white-space: pre-wrap;
  line-height: 1.6;
  color: #1F2937;
  background: #f7f9fc;
  border-left: 3px solid #273f73;
  border-radius: 6px;
  padding: 0.85rem 1rem;
}

/* --- radar legend --- */
.radar-legend {
  margin-top: 0.4rem;
  font-size: 0.86rem;
  color: #4b5563;
}
.radar-legend-row {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.15rem 0;
  line-height: 1.45;
}
.radar-legend-key {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  flex: none;
  margin-top: 0.35rem;
}
.radar-legend em { color: #8a94a6; }

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


def assessed_criteria(ratings: list) -> list:
    """Criteria this student has actually been graded on at least once.

    A criterion that has never been graded must not be plotted as zero -- on a
    radar that reads as "very weak at this" rather than "not assessed yet".
    """
    if not ratings:
        return []
    df = pd.DataFrame(ratings)
    return [
        c for c in RATING_CRITERIA
        if c[0] in df.columns and df[c[0]].notna().any()
    ]


def build_radar_chart(ratings: list) -> go.Figure:
    """Radar of the communication criteria, averaged over all check-ins.

    Only criteria with at least one grade are plotted. Axes use the short
    Vietnamese labels so they stay legible on a phone; the full descriptions
    are listed beneath the chart by the caller.
    """
    df = pd.DataFrame(ratings)
    values, labels = [], []
    for field, _en, short_vi, _full_vi, _color in assessed_criteria(ratings):
        values.append(round(df[field].dropna().mean(), 2))
        labels.append(short_vi)
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
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 5], tickvals=[1, 2, 3, 4, 5], tickfont=dict(size=10)),
            angularaxis=dict(tickfont=dict(size=11)),
        ),
        showlegend=False,
        # Generous side margins: Vietnamese axis labels are long and get
        # clipped at the container edge on a phone otherwise.
        margin=dict(l=70, r=70, t=40, b=40),
        height=340,
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


def criteria_average(ratings: list) -> pd.DataFrame:
    """Per-check-in mean across the six communication criteria (homework excluded)."""
    df = pd.DataFrame(ratings)
    df["rating_date"] = pd.to_datetime(df["rating_date"])
    value_cols = [f for f, _e, _s, _v, _c in RATING_CRITERIA if f in df.columns]
    df["avg_score"] = df[value_cols].mean(axis=1, skipna=True) if value_cols else pd.NA
    return df.dropna(subset=["avg_score"]).sort_values("rating_date")


def build_trend_chart(ratings: list) -> alt.Chart:
    df = criteria_average(ratings)

    # Tick only on days a check-in actually happened -- Altair's default puts a
    # label every other calendar day, which is unreadable on a phone.
    tick_values = [d.isoformat() for d in df["rating_date"].dt.date]
    x_axis = alt.X(
        "rating_date:T",
        title=VI_TEXT["chart_date"],
        axis=alt.Axis(values=tick_values, format="%d/%m", labelAngle=-45),
    )

    area = (
        alt.Chart(df)
        .mark_area(interpolate="monotone", line={"color": "#273f73"}, color="#a9bad9", opacity=0.4)
        .encode(
            x=x_axis,
            y=alt.Y("avg_score:Q", title=VI_TEXT["chart_avg_score"], scale=alt.Scale(domain=[1, 5])),
            tooltip=[
                alt.Tooltip("rating_date:T", title=VI_TEXT["chart_date"], format="%d/%m/%Y"),
                alt.Tooltip("avg_score:Q", title=VI_TEXT["chart_avg_score"], format=".1f"),
            ],
        )
    )
    points = (
        alt.Chart(df)
        .mark_point(color="#273f73", filled=True, size=50)
        .encode(x="rating_date:T", y="avg_score:Q")
    )
    return (area + points).properties(height=280)


def build_criterion_breakdown_chart(ratings: list) -> alt.Chart:
    """One line per communication criterion, for the optional detail expander."""
    df = pd.DataFrame(ratings)
    df["rating_date"] = pd.to_datetime(df["rating_date"])
    label_map = {f: full_vi for f, _e, _s, full_vi, _c in RATING_CRITERIA}
    color_map = {full_vi: color for _f, _e, _s, full_vi, color in RATING_CRITERIA}
    value_cols = [f for f in label_map if f in df.columns]

    long_df = df.melt(id_vars="rating_date", value_vars=value_cols, var_name="criterion", value_name="stars")
    long_df["criterion"] = long_df["criterion"].map(label_map)
    long_df = long_df.dropna(subset=["stars"])

    return (
        alt.Chart(long_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("rating_date:T", title=VI_TEXT["chart_date"]),
            y=alt.Y("stars:Q", title=VI_TEXT["chart_avg_score"], scale=alt.Scale(domain=[1, 5])),
            color=alt.Color(
                "criterion:N",
                title=None,
                scale=alt.Scale(domain=list(color_map.keys()), range=list(color_map.values())),
                legend=alt.Legend(orient="bottom", columns=2),
            ),
            tooltip=["rating_date:T", "criterion:N", "stars:Q"],
        )
        .properties(height=300)
    )


def compute_streak(ratings: list) -> tuple:
    """Consecutive-calendar-weeks streak of strong communication performance.

    A week qualifies when the student's mean across the six communication
    criteria is >= 4. Weeks with no check-in at all are *skipped*, not counted
    as failures -- otherwise the badge would punish a student for a week the
    teacher simply didn't get round to grading, or one they were absent for.

    Computed fresh from history on every render rather than stored as a mutable
    counter, so it can never drift if a check-in is later edited or backfilled.
    """
    week_scores = {}
    for r in ratings:
        scores = [r.get(f) for f, _e, _s, _v, _c in RATING_CRITERIA if r.get(f) is not None]
        if not scores:
            continue
        d = datetime.strptime(r["rating_date"], "%Y-%m-%d").date()
        iso_year, iso_week, _ = d.isocalendar()
        # Several check-ins in one week: take the best week-average available.
        avg = sum(scores) / len(scores)
        key = (iso_year, iso_week)
        week_scores[key] = max(week_scores.get(key, 0), avg)

    if not week_scores:
        return 0, 0

    # Only weeks that were actually graded participate; ungraded weeks are
    # invisible to the run rather than breaking it.
    graded = sorted((date.fromisocalendar(y, w, 1), avg) for (y, w), avg in week_scores.items())

    longest = current = 0
    for monday, avg in graded:
        current = current + 1 if avg >= 4 else 0
        longest = max(longest, current)

    return current, longest


# ---------------------------------------------------------------------------
# Parent portal (no login, read-only, reached via ?token=...)
# ---------------------------------------------------------------------------

def _session_stars_html(rating: dict) -> str:
    """Star rows for one check-in, skipping criteria that weren't graded."""
    rows = []
    for field, _en, _short, full_vi, _color in RATING_CRITERIA:
        value = rating.get(field)
        if value:
            rows.append(
                f'<div class="session-stars-row"><span class="session-stars-label">{full_vi}</span>'
                f"{_stars_html(value, total=5)}</div>"
            )
    homework = rating.get(HOMEWORK_FIELD)
    if homework:
        rows.append(
            f'<div class="session-stars-row"><span class="session-stars-label">{HOMEWORK_VI}</span>'
            f"{_stars_html(homework, total=5)}</div>"
        )
    return "".join(rows)


def _radar_legend_html(graded_fields: set) -> str:
    """Legend under the radar: full descriptions, with ungraded criteria greyed.

    Listing the ungraded ones explicitly is deliberate -- otherwise a criterion
    simply vanishing from the chart looks like a glitch to a parent.
    """
    rows = []
    for field, _en, short_vi, full_vi, color in RATING_CRITERIA:
        is_graded = field in graded_fields
        swatch = color if is_graded else "#d5dae5"
        suffix = "" if is_graded else f' <em>({VI_TEXT["not_yet_graded"]})</em>'
        rows.append(
            f'<div class="radar-legend-row"><span class="radar-legend-key" '
            f'style="background:{swatch}"></span>'
            f"<span><strong>{short_vi}</strong> — {full_vi}{suffix}</span></div>"
        )
    return "".join(rows)


def _note_preview(note: str, limit: int = 70) -> str:
    if not note:
        return "—"
    first_line = note.strip().splitlines()[0]
    return first_line if len(first_line) <= limit else first_line[:limit].rstrip() + "…"


def render_comment_timeline(ratings: list):
    """Full-width session history: newest expanded, older ones collapsed."""
    st.markdown(f"#### 💬 {VI_TEXT['comment_history']}")
    st.caption(VI_TEXT["comment_history_sub"])

    if not ratings:
        st.write(VI_TEXT["no_comments"])
        return

    newest_first = list(reversed(ratings))
    latest, older = newest_first[0], newest_first[1:]

    st.markdown(
        f'<div class="session-latest-header">{VI_TEXT["latest_label"]} · '
        f'{format_date_vi(latest["rating_date"])}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="session-stars">{_session_stars_html(latest)}</div>', unsafe_allow_html=True)
    if latest.get("notes"):
        st.markdown(f'<div class="session-note">{latest["notes"]}</div>', unsafe_allow_html=True)
    else:
        st.caption("Chưa có nhận xét cho buổi này.")

    for r in older:
        label = f"{format_date_vi(r['rating_date'])} — {_note_preview(r.get('notes'))}"
        with st.expander(label):
            st.markdown(f'<div class="session-stars">{_session_stars_html(r)}</div>', unsafe_allow_html=True)
            if r.get("notes"):
                st.markdown(f'<div class="session-note">{r["notes"]}</div>', unsafe_allow_html=True)
            else:
                st.caption("Chưa có nhận xét cho buổi này.")


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
            graded = assessed_criteria(ratings)
            graded_fields = {c[0] for c in graded}
            if len(graded) >= 3:
                st.plotly_chart(build_radar_chart(ratings), use_container_width=True)
            elif graded:
                # Too few axes for a meaningful polygon -- fall back to stars.
                df_avg = pd.DataFrame(ratings)
                for field, _en, _short, full_vi, _color in graded:
                    avg = round(df_avg[field].dropna().mean())
                    st.markdown(
                        f'<div class="session-stars-row"><span class="session-stars-label">{full_vi}'
                        f"</span>{_stars_html(avg, total=5)}</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.write(VI_TEXT["not_enough_data"])

            if graded:
                st.markdown(
                    f'<div class="radar-legend">{_radar_legend_html(graded_fields)}</div>',
                    unsafe_allow_html=True,
                )
    with col2:
        with st.container(border=True):
            st.markdown(f"#### 📈 {VI_TEXT['learning_trend']}")
            if ratings:
                st.altair_chart(build_trend_chart(ratings), use_container_width=True)
                with st.expander(VI_TEXT["per_criterion"]):
                    st.altair_chart(build_criterion_breakdown_chart(ratings), use_container_width=True)
            else:
                st.write(VI_TEXT["not_enough_data"])

    # Row 2: teacher comments, full width -- the heart of the page
    with st.container(border=True):
        render_comment_timeline(ratings)

    # Row 3: homework gauge + milestones
    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            st.markdown(f"#### 📚 {VI_TEXT['homework_gauge']}")
            if ratings and ratings_df[HOMEWORK_FIELD].notna().any():
                st.plotly_chart(
                    build_gauge_figure(HOMEWORK_FIELD, HOMEWORK_VI, HOMEWORK_COLOR, ratings_df),
                    use_container_width=True,
                )
            else:
                st.write(VI_TEXT["not_enough_data"])

    with col4:
        with st.container(border=True):
            st.markdown(f"#### 🏅 {VI_TEXT['milestones']}")
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


def render_past_checkins(client: Client, student: dict):
    """Edit or delete previous check-ins.

    Parents read these notes, so a typo needs to be fixable without going
    into Supabase by hand.
    """
    past = (
        client.table("student_ratings")
        .select("*")
        .eq("student_id", student["id"])
        .order("rating_date", desc=True)
        .execute()
        .data
    )
    if not past:
        st.write("No check-ins recorded for this student yet.")
        return

    for r in past:
        preview = _note_preview(r.get("notes"), limit=60)
        with st.expander(f"{format_date_vi(r['rating_date'])} — {preview}"):
            with st.form(f"edit_checkin_{r['id']}"):
                edited = {}
                cols = st.columns(3)
                for i, (field, label, _s, _v, _c) in enumerate(RATING_CRITERIA):
                    with cols[i % 3]:
                        current = r.get(field)
                        edited[field] = st.selectbox(
                            label,
                            [None, 1, 2, 3, 4, 5],
                            index=0 if current is None else current,
                            format_func=lambda v: "—" if v is None else _stars_plain(v, total=5),
                            key=f"edit_{field}_{r['id']}",
                        )
                current_hw = r.get(HOMEWORK_FIELD)
                edited[HOMEWORK_FIELD] = st.selectbox(
                    HOMEWORK_EN,
                    [None, 1, 2, 3, 4, 5],
                    index=0 if current_hw is None else current_hw,
                    format_func=lambda v: "—" if v is None else _stars_plain(v, total=5),
                    key=f"edit_hw_{r['id']}",
                )
                new_notes = st.text_area(
                    "Notes (visible to the parent)",
                    value=r.get("notes") or "",
                    height=220,
                    key=f"edit_notes_{r['id']}",
                )
                confirm = st.checkbox(
                    "Yes, permanently delete this check-in and its notes", key=f"confirm_ci_{r['id']}"
                )
                save_col, del_col = st.columns(2)
                save = save_col.form_submit_button("Save changes")
                delete = del_col.form_submit_button("Delete check-in", type="secondary")

            if save:
                client.table("student_ratings").update(
                    {"notes": new_notes or None, **edited}
                ).eq("id", r["id"]).execute()
                st.success("Check-in updated.")
                st.rerun()

            if delete and not confirm:
                st.warning("Check the confirmation box above before deleting.")

            if delete and confirm:
                client.table("student_ratings").delete().eq("id", r["id"]).execute()
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

    st.markdown("#### Add a progress check-in")
    with st.form("rating_form", clear_on_submit=True):
        rating_date = st.date_input("Date", value=date.today())
        rating_values = {}

        st.caption("In-class communication")
        for row_start in (0, 3):
            row_cols = st.columns(3)
            for col, (field, label, _s, _v, _c) in zip(row_cols, RATING_CRITERIA[row_start : row_start + 3]):
                with col:
                    st.write(label)
                    choice = st.feedback("stars", key=f"rating_{field}")
                    rating_values[field] = (choice + 1) if choice is not None else None

        st.caption("At home")
        st.write(HOMEWORK_EN)
        hw_choice = st.feedback("stars", key=f"rating_{HOMEWORK_FIELD}")
        rating_values[HOMEWORK_FIELD] = (hw_choice + 1) if hw_choice is not None else None

        notes = st.text_area("Notes (visible to the parent)", height=200, key="rating_notes")
        if st.form_submit_button("Add check-in"):
            try:
                client.table("student_ratings").insert(
                    {
                        "student_id": student["id"],
                        "rating_date": rating_date.isoformat(),
                        "notes": notes or None,
                        **rating_values,
                    }
                ).execute()
                st.success("Check-in added.")
            except Exception as e:
                if "student_ratings_one_per_day" in str(e):
                    st.error(
                        f"{student['name']} already has a check-in on "
                        f"{format_date_vi(rating_date.isoformat())}. Edit it under "
                        "'Past check-ins' below instead of adding a second one."
                    )
                else:
                    st.error(f"Could not save check-in: {e}")

    st.markdown("#### Past check-ins")
    render_past_checkins(client, student)

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
        page = st.radio("Section", ["Classes", "Students", "Track progress"])

    render_hero("ESL Progress Dashboard")

    if page == "Classes":
        render_classes(client)
    elif page == "Students":
        render_students(client)
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
