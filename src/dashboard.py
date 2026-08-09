import streamlit as st
import datetime as datetime_lib
from datetime import date
from src.database import SessionLocal, user, usersubject, study_log, topic, subject
from src.scheduler import calculate_subject_priorities

def render_dashboard_tab():
    db = SessionLocal()
    st.title("📊 Priority Dashboard & Academic Overview")
    st.info("Your central hub for exam count-downs, study trends, and overall readiness.")

    db_user = db.query(user).filter(user.id == st.session_state.user_id).first()

    if not db_user.global_exam_start:
        db_user.global_exam_start = str(date.today())
        db.commit()

    stored_date = datetime_lib.datetime.strptime(db_user.global_exam_start, "%Y-%m-%d").date()
    with st.expander("⚙️ Global Exam Block Window Settings", expanded=False):
        new_global_date = st.date_input("Semester Theory Exams Start Date", value=stored_date)
        if str(new_global_date) != db_user.global_exam_start:
            db_user.global_exam_start = str(new_global_date)
            db.commit()
            st.rerun()

    global_exam_start_val = datetime_lib.datetime.strptime(db_user.global_exam_start, "%Y-%m-%d").date()

    user_subjects = db.query(usersubject).filter(usersubject.user_id == st.session_state.user_id).all()
    all_logs = db.query(study_log).filter(study_log.user_id == st.session_state.user_id).all()
    
    col_m1, col_m2 = st.columns(2)
    col_m1.metric(label="Enrolled Subjects", value=len(user_subjects))
    total_study_mins = sum(log.duration_minutes for log in all_logs) if all_logs else 0
    col_m2.metric(label="Total Study Time", value=f"{total_study_mins} mins")

    st.markdown("---")

    if not user_subjects:
        st.warning("No subjects enrolled yet. Go to 'Manage Subjects' to add courses and set your exam dates.")
    else:
        processed_subjects = calculate_subject_priorities(
            user_subjects, db, subject, topic, global_exam_start_val
        )

        st.subheader("Daily Focus & Priorities")
        st.write(f"Active Global Block Start: **{global_exam_start_val}**")
        
        for rank, item in enumerate(processed_subjects, start=1):
            sub = item["sub_obj"]
            total_topics = item["total_topics"]
            covered_topics = item["covered_topics"]
            days_left = item["days_left"]
            
            topic_pct = (covered_topics / total_topics) if total_topics > 0 else 0.0
            readiness_score = int(topic_pct * 100)

            date_label = f"{item['effective_date']} {'(Custom)' if item['is_individual'] else '(Block Window)'}"
            
            if days_left < 0:
                timeline_msg = f"Exam window passed ({abs(days_left)} days ago)"
            elif days_left == 0:
                timeline_msg = "🚨 Exam is TODAY!"
            else:
                timeline_msg = f"⏳ {days_left} days left"

            with st.container():
                if rank <= 2 and item["remaining_topics"] > 0:
                    st.markdown(f"### ⚡ Process [CPU Focus]: {sub.name} ({sub.category})")
                else:
                    st.markdown(f"#### 📖 {sub.name} ({sub.category})")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Readiness", f"{readiness_score}%")
                c2.metric("Remaining Topics", item["remaining_topics"])
                c3.metric("Target Date", date_label)
                c4.metric("Timeline", timeline_msg)

                if readiness_score >= 80:
                    st.success("🟢 Status: Process Optimized / On Track.")
                elif readiness_score >= 40:
                    st.warning("🟡 Status: Moderate Load. Keep clearing pending topics.")
                else:
                    st.error("🔴 Status: High Priority Bottleneck. Recommended focus for today.")

                st.markdown("---")

        st.subheader("📈 Study Consistency Line Graph")
        if all_logs:
            import pandas as pd
            log_data = [{"Date": log.timestamp.split()[0], "Minutes": log.duration_minutes} for log in all_logs if log.timestamp]
            df_logs = pd.DataFrame(log_data)
            df_grouped = df_logs.groupby("Date").sum().reset_index().sort_values("Date")
            st.line_chart(df_grouped.set_index("Date"))
        else:
            st.info("No study consistency logs recorded yet.")

    db.close()