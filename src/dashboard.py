
import streamlit as st
from datetime import date, datetime, timedelta
from src.database import SessionLocal, user, usersubject, study_log, topic, subject


def render_dashboard_tab():

    db = SessionLocal()

    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #F7F4FF, #F4F8FF, #FFF7F2);
    }

    [data-testid="stHeader"] { background: transparent; }

    .block-container {
        max-width: 1100px;
        padding-top: 2.2rem;
        padding-bottom: 3rem;
    }

    h1 { color: #493D67 !important; font-weight: 700 !important; }
    h2, h3 { color: #574A75 !important; }

    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #E8E0F5;
        border-radius: 16px;
        padding: 15px 18px;
        box-shadow: 0 3px 12px rgba(91,74,125,0.05);
    }

    [data-testid="stMetricLabel"] { color: #817695 !important; }
    [data-testid="stMetricValue"] { color: #51446F !important; }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255,255,255,0.92);
        border: 1px solid #E7E0F1;
        border-radius: 18px;
        padding: 12px;
        box-shadow: 0 4px 15px rgba(91,74,125,0.04);
    }

    [data-testid="stProgress"] > div {
        background: #E9E3F4;
        border-radius: 20px;
        height: 9px;
    }

    [data-testid="stProgress"] > div > div {
        background: #A995D5;
        border-radius: 20px;
    }

    .stButton > button {
        background: #8E7AB8;
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
    }

    .stButton > button:hover {
        background: #75619F;
        color: white;
    }

    [data-testid="stExpander"] {
        background: rgba(255,255,255,0.85);
        border: 1px solid #E7E0F1;
        border-radius: 14px;
    }

    .exam-card {
        background: linear-gradient(120deg, #EAE3FA, #E5EFFD);
        border: 1px solid #DCD2F0;
        border-radius: 20px;
        padding: 24px;
        margin: 10px 0 20px 0;
    }

    .exam-label {
        color: #786695;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .exam-name {
        color: #493D67;
        font-size: 25px;
        font-weight: 700;
        margin-top: 8px;
    }

    .exam-count {
        color: #715B9B;
        font-size: 34px;
        font-weight: 700;
        margin-top: 5px;
    }

    .exam-date {
        color: #786D8D;
        font-size: 14px;
        margin-top: 5px;
    }

    .study-card {
        background: linear-gradient(120deg, #E5F4EC, #EFF8F2);
        border: 1px solid #D2EADD;
        border-radius: 18px;
        padding: 20px;
        margin-bottom: 15px;
    }

    .study-label {
        color: #62836F;
        font-size: 13px;
        font-weight: 600;
    }

    .study-value {
        color: #386B4B;
        font-size: 30px;
        font-weight: 700;
        margin-top: 5px;
    }

    .subject-name {
        color: #51446F;
        font-size: 18px;
        font-weight: 700;
    }

    .subject-category {
        color: #8B8299;
        font-size: 12px;
        margin-top: 2px;
    }

    .section-caption {
        color: #817695;
        font-size: 14px;
        margin-bottom: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

    try:
        user_id = st.session_state.user_id

        db_user = db.query(user).filter(user.id == user_id).first()

        if not db_user:
            st.error("User not found.")
            return

        st.title("Your Study Space")
        st.caption("A calm space to plan, learn and make progress.")

        # Exam date settings
        stored_date = None

        if db_user.global_exam_start:
            try:
                stored_date = datetime.strptime(
                    db_user.global_exam_start, "%Y-%m-%d"
                ).date()
            except ValueError:
                pass

        with st.expander("Semester Exam Date Settings"):
            new_date = st.date_input(
                "Semester theory exams start date",
                value=stored_date or date.today()
            )

            if st.button("Save exam date"):
                db_user.global_exam_start = str(new_date)
                db.commit()
                st.success("Exam date updated.")
                st.rerun()

        # Fetch data
        enrollments = (
            db.query(usersubject)
            .filter(usersubject.user_id == user_id)
            .all()
        )

        all_logs = (
            db.query(study_log)
            .filter(study_log.user_id == user_id)
            .all()
        )

        if not enrollments:
            st.info(
                "You haven't added any subjects yet. "
                "Start by adding subjects in Manage Subjects."
            )
            return

        # Prepare subject information
        subject_data = []

        for enrollment in enrollments:

            sub = db.query(subject).filter(
                subject.id == enrollment.subject_id
            ).first()

            if not sub:
                continue

            topics = db.query(topic).filter(
                topic.subject_id == sub.id
            ).all()

            total_topics = len(topics)

            if total_topics:
                total_confidence = sum(
                    t.confidence_score or 0 for t in topics
                )
                readiness = int(
                    (total_confidence / (total_topics * 10)) * 100
                )
                readiness = max(0, min(100, readiness))

                pending_topics = sum(
                    1 for t in topics if (t.confidence_score or 0) < 7
                )
            else:
                readiness = 0
                pending_topics = 0

            # Individual exam date takes precedence
            exam_date = None

            if enrollment.exam_date and enrollment.exam_date != "None":
                try:
                    exam_date = datetime.strptime(
                        enrollment.exam_date, "%Y-%m-%d"
                    ).date()
                except ValueError:
                    pass

            if not exam_date and stored_date:
                exam_date = stored_date

            days_left = (
                (exam_date - date.today()).days
                if exam_date else None
            )

            subject_data.append({
                "subject": sub,
                "readiness": readiness,
                "total_topics": total_topics,
                "pending_topics": pending_topics,
                "exam_date": exam_date,
                "days_left": days_left
            })

        # Welcome
        st.subheader("Welcome back!")
        st.write("Take things one topic at a time. You're making progress.")

        # Upcoming exam
        st.markdown("## Upcoming Exams")

        upcoming_exams = [
            item for item in subject_data
            if item["exam_date"] and item["days_left"] >= 0
        ]

        upcoming_exams.sort(key=lambda x: x["days_left"])

        if upcoming_exams:
            nearest = upcoming_exams[0]

            if nearest["days_left"] == 0:
                countdown = "Your exam is today"
            else:
                countdown = f'{nearest["days_left"]} days to go'

            st.markdown(f"""
            <div class="exam-card">
                <div class="exam-label">Your next exam</div>
                <div class="exam-name">{nearest["subject"].name}</div>
                <div class="exam-count">{countdown}</div>
                <div class="exam-date">
                    {nearest["exam_date"].strftime("%d %B %Y")}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if len(upcoming_exams) > 1:
                with st.expander("See other exam dates"):
                    for item in upcoming_exams[1:]:
                        st.write(
                            f'{item["subject"].name} — '
                            f'{item["exam_date"].strftime("%d %B %Y")}'
                        )
        else:
            st.info("No upcoming exam dates. Add dates to your subjects.")

        # Weekly study summary
        st.markdown("## Your Study This Week")

        week_start = date.today() - timedelta(
            days=date.today().weekday()
        )

        weekly_minutes = 0

        for log in all_logs:
            if log.created_at:
                try:
                    log_date = datetime.strptime(
                        log.created_at, "%Y-%m-%d %H:%M"
                    ).date()

                    if week_start <= log_date <= date.today():
                        weekly_minutes += log.duration_minutes or 0

                except ValueError:
                    continue

        hours = weekly_minutes // 60
        minutes = weekly_minutes % 60

        st.markdown(f"""
        <div class="study-card">
            <div class="study-label">TIME INVESTED THIS WEEK</div>
            <div class="study-value">{hours}h {minutes}m</div>
            <div class="study-label">
                Every focused session counts.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Subject cards
        st.markdown("## My Subjects")
        st.markdown(
            '<div class="section-caption">'
            'Your subjects and their current learning progress.'
            '</div>',
            unsafe_allow_html=True
        )

        pastel_colors = [
            ("#EFF3FF", "#DCE5FC"),
            ("#EDF7F0", "#D9EEDF"),
            ("#FFF3EA", "#F9E1D0"),
            ("#F5EEFF", "#E7DAF8")
        ]

        for index, item in enumerate(subject_data):

            sub = item["subject"]
            bg_color, border_color = pastel_colors[
                index % len(pastel_colors)
            ]

            with st.container(border=True):

                st.markdown(
                    f'<div class="subject-name">{sub.name}</div>',
                    unsafe_allow_html=True
                )

                if sub.category:
                    st.caption(sub.category)

                col1, col2 = st.columns(2)

                col1.metric("Readiness", f'{item["readiness"]}%')
                col2.metric("Topics to review", item["pending_topics"])

                st.progress(item["readiness"] / 100)

                if item["total_topics"] == 0:
                    st.caption("No topics added yet.")

                if item["exam_date"]:
                    exam_text = item["exam_date"].strftime("%d %B %Y")

                    if item["days_left"] < 0:
                        st.caption(f"Exam: {exam_text} · Date passed")
                    elif item["days_left"] == 0:
                        st.caption(f"Exam: {exam_text} · Today")
                    else:
                        st.caption(
                            f'Exam: {exam_text} · '
                            f'{item["days_left"]} days remaining'
                        )
                else:
                    st.caption("Exam date not set.")

        st.markdown("---")
        st.caption(
            "Keep showing up for your goals. "
            "Consistency matters more than perfection."
        )

    finally:
        db.close()
