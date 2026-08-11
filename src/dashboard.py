import streamlit as st
import datetime as datetime_lib
from datetime import date
from src.database import SessionLocal, user, usersubject, study_log, topic, subject
from src.scheduler import calculate_subject_priorities
import pandas as pd

def render_dashboard_tab():
    db = SessionLocal()
    st.title("📊 Priority Dashboard & Academic Overview")
    st.info("Your central hub for exam count-downs, study trends, and overall readiness.")

    db_user = db.query(user).filter(user.id == st.session_state.user_id).first()

    if not db_user.global_exam_start:
        db_user.global_exam_start = str(date.today())
        db.commit()

    stored_date = datetime_lib.datetime.strptime(db_user.global_exam_start, "%Y-%m-%d").date()
    with st.expander("Global Exam Block Window Settings", expanded=False):
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
        st.write(f"Active Global Exam Start: **{global_exam_start_val}**")
        
        for rank, item in enumerate(processed_subjects, start=1):
            sub = item["sub_obj"]
            total_topics = item["total_topics"]
            readiness_score = item["readiness_score"]  # Now derived from 1-10 confidence scale avg
            remaining_topics = item["remaining_topics"]
            days_left = item["days_left"]
            

            date_label = f"{item['effective_date']} {'(Custom)' if item['is_individual'] else '(Block Window)'}"
            
            if days_left < 0:
                timeline_msg = f"Exam window passed ({abs(days_left)} days ago)"
            elif days_left == 0:
                timeline_msg = "🚨 Exam is TODAY!"
            else:
                timeline_msg = f"⏳ {days_left} days left"

            with st.container():
                if rank <= 2 and remaining_topics > 0:
                    st.markdown(f"High Priority Process: {sub.name} (`{sub.category}`)")
                else:
                    st.markdown(f"📖 {sub.name} (`{sub.category}`)")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Readiness Score", f"{readiness_score}%")
                c2.metric("Topics Needing Review", remaining_topics)
                c3.metric("Target Date", date_label)
                c4.metric("Timeline", timeline_msg)

                if total_topics == 0:
                    st.warning("🔔 Kindly add some topics!")
                elif readiness_score >= 80:
                    st.success("🟢 Status: Process Optimized / On Track.")
                elif readiness_score >= 40:
                    st.warning("🟡 Status: Moderate Load. Keep clearing pending topics.")
                else:
                    st.error("🔴 Status: High Priority Bottleneck. Recommended focus for today.")

                st.markdown("---")
        # Workload and completion analysis chart
        st.subheader("Workload & Completion Analytics")
        chart_data = []
        for item in processed_subjects:
            sub = item["sub_obj"]
            chart_data.append({
                "Subject": sub.name,
                "Readiness Score (%)": item["readiness_score"],
                "Low Confidence Topics": item["remaining_topics"]
            })
        
        df_chart = pd.DataFrame(chart_data)
        if not df_chart.empty:
            st.caption("Overall Subject Readiness Overview (%)")
            st.bar_chart(df_chart.set_index("Subject")[["Readiness Score (%)", "Low Confidence Topics"]])
        else:
            st.info("Add topics to subjects to view analytics.")

        st.markdown("---")

        #individual subject dropdown
        st.subheader("Individual Enrollment Status")
        
        subject_options_map = {item["name"]: item for item in processed_subjects}
        choosen_subject_name = st.selectbox("Choose Enrolled Subject", list(subject_options_map.keys()))

        if choosen_subject_name:
            selected_data = subject_options_map[choosen_subject_name]
            sel_sub = selected_data["sub_obj"]
            sel_tot = selected_data["total_topics"]
            sel_rem = selected_data["remaining_topics"]
            sel_score = selected_data["readiness_score"]
            sel_days = selected_data["days_left"]
            sel_date = selected_data["effective_date"]

            sel_pct = sel_score / 100.0

            with st.container(border=True):
                st.markdown(f"📖 {sel_sub.name} (`{sel_sub.category}` — {sel_sub.credits} Credits)")
                
                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric("Readiness Score", f"{sel_score}%")
                sc2.metric("Total Topics", f"{sel_tot} topics")
                sc3.metric("Remaining Topics", f"{sel_rem} topics")
                sc4.metric("Days Left", f"{sel_days} days", f"Target: {sel_date}")

                st.progress(sel_pct)

                if total_topics == 0:
                    st.warning("🔔 Kindly add some topics!")
                elif sel_score >= 80:
                    st.success("🟢 Status: Course execution is optimized and well on track.")
                elif sel_score >= 40:
                    st.warning("🟡 Status: Moderate workload. Keep knocking out pending topics.")
                else:
                    st.error("🔴 Status: High priority bottleneck. Requires immediate study focus.")

        st.markdown("---")

        st.subheader("📈 Study Consistency Line Graph")
        if all_logs:
            log_data = [{"Date": log.created_at.split()[0], "Minutes": log.duration_minutes} for log in all_logs if log.created_at]
            df_logs = pd.DataFrame(log_data)
            df_grouped = df_logs.groupby("Date").sum().reset_index().sort_values("Date")
            st.line_chart(df_grouped.set_index("Date"))
        else:
            st.info("No study consistency logs recorded yet.")

    db.close()