import streamlit as st
import datetime as datetime_lib
from datetime import timedelta
from src.database import SessionLocal, usersubject, subject, study_log

def render_study_logs_tab():
    st.title("Study Logs & Reflection Journal")
    st.write("Record what you accomplished, track difficulties or roadblocks, and review your learning history over time.")

    db = SessionLocal()
    user_subjects = db.query(usersubject).filter(usersubject.user_id == st.session_state.user_id).all()

    if not user_subjects:
        st.warning("Please enroll in subjects under 'Manage Subjects' before writing study logs.")
    else:
        subject_options = {}
        for enr in user_subjects:
            sub = db.query(subject).filter(subject.id == enr.subject_id).first()
            if sub:
                subject_options[sub.name] = sub.id

        # --- SECTION 1: ADD NEW STUDY LOG FORM ---
        with st.form("add_study_log_form"):
            st.subheader("✍️ Write a New Log Entry")
            
            selected_sub_name = st.selectbox("Select Subject", list(subject_options.keys()))
            selected_sub_id = subject_options[selected_sub_name]
            
            duration_mins = st.number_input("Time Spent (in minutes)", min_value=5, max_value=600, value=60, step=5)
            
            log_notes = st.text_area(
                "Session Reflection & Roadblocks", 
                placeholder="e.g., Completed Concurrency Control up to 2PL protocols. Got stuck on strict vs rigorous serializability graphs, need to review tomorrow."
            )
            
            submit_log = st.form_submit_button("Save Log Entry")
            
            if submit_log:
                current_timestamp = datetime_lib.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                new_log = study_log(
                    user_id=st.session_state.user_id,
                    subject_id=selected_sub_id,
                    duration_minutes=duration_mins,
                    timestamp=current_timestamp,
                    notes=log_notes
                )
                db.add(new_log)
                db.commit()
                st.success("Study log saved successfully! Your consistency graph and journal have been updated.")
                st.rerun()

        st.markdown("---")

        # --- SECTION 2: VIEW AND FILTER PAST LOGS ---
        st.subheader("📖 Past Reflection Logs")
        
        time_filter = st.selectbox(
            "Filter History By", 
            ["Last 24 Hours", "Last 7 Days", "Last 1 Month", "Last 3 Months", "All Logs"]
        )

        now = datetime_lib.datetime.now()
        
        if time_filter == "Last 24 Hours":
            threshold = now - timedelta(hours=24)
        elif time_filter == "Last 7 Days":
            threshold = now - timedelta(days=7)
        elif time_filter == "Last 1 Month":
            threshold = now - timedelta(days=30)
        elif time_filter == "Last 3 Months":
            threshold = now - timedelta(days=90)
        else:
            threshold = None  # All logs

        query = db.query(study_log).filter(study_log.user_id == st.session_state.user_id)
        all_user_logs = query.all()

        filtered_logs = []
        for log in all_user_logs:
            if log.timestamp:
                try:
                    log_dt = datetime_lib.datetime.strptime(log.timestamp, "%Y-%m-%d %H:%M:%S")
                    if threshold is None or log_dt >= threshold:
                        filtered_logs.append((log, log_dt))
                except:
                    filtered_logs.append((log, now))

        filtered_logs = sorted(filtered_logs, key=lambda x: x[1], reverse=True)

        if filtered_logs:
            st.write(f"Showing **{len(filtered_logs)}** log entry/entries for *{time_filter}*:")
            for log, log_dt in filtered_logs:
                logged_sub = db.query(subject).filter(subject.id == log.subject_id).first()
                sub_name_disp = logged_sub.name if logged_sub else "Unknown Subject"
                
                with st.container():
                    col_l1, col_l2 = st.columns([0.7, 0.3])
                    col_l1.markdown(f"### 📘 {sub_name_disp}")
                    col_l2.write(f"⏱️ **{log.duration_minutes} mins**\n\n📅 *{log.timestamp}*")
                    
                    if log.notes:
                        st.info(f"**Reflection / Roadblocks:**\n\n{log.notes}")
                    else:
                        st.caption("_No written notes provided for this session._")
                    
                    st.markdown("---")
        else:
            st.info(f"No study logs found for the selected filter ({time_filter}). Start writing logs above to build your history!")

    db.close()