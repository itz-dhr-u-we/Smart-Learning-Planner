import streamlit as st
import datetime as datetime_lib
from datetime import timedelta
from src.database import SessionLocal, usersubject, subject, study_log
import json 
from src.helper import get_ai_tutor_response

def render_study_logs_tab():
    st.title("Study Logs & AI Doubt Tutor")
    st.write("Record what you accomplished, track difficulties or roadblocks, and review your learning history over time.")

    db = SessionLocal()
    user_subjects = db.query(usersubject).filter(usersubject.user_id == st.session_state.user_id).all()

    if not user_subjects:
        st.warning("Please enroll in subjects under 'Manage Subjects' before writing study logs.")
        db.close()
        return
    else:
        subject_options = {}
        for enr in user_subjects:
            sub = db.query(subject).filter(subject.id == enr.subject_id).first()
            if sub:
                subject_options[sub.name] = sub.id

        # SECTION 1: ADD NEW STUDY LOG FORM 
        with st.form("add_study_log_form"):
            st.subheader("Write a New Log Entry")
            
            selected_sub_name = st.selectbox("Select Subject", list(subject_options.keys()))
            selected_sub_id = subject_options[selected_sub_name]
            
            duration_mins = st.number_input("Time Spent (in minutes)", min_value=5, max_value=600, value=60, step=5)
            
            log_notes = st.text_area(
                "Session Reflection & Roadblocks", 
                placeholder="e.g., Completed Concurrency Control up to 2PL protocols. Got stuck on strict vs rigorous serializability graphs, need to review tomorrow."
            )
            col_btn1, col_btn2 = st.columns(2)
            save_only = col_btn1.form_submit_button("Save Log Entry")
            save_and_ai = col_btn2.form_submit_button("Save & Ask AI Tutor")
            
            
            if (save_only or save_and_ai) and log_notes.strip():
                current_timestamp = datetime_lib.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                initial_chat = []
                if save_and_ai:
                    prompt_context = f"The student is studying {selected_sub_name}. Their study log / doubt is: '{log_notes}'. Provide a direct, helpful explanation and end with a short active recall follow-up question to test their understanding."
                    ai_response = get_ai_tutor_response(selected_sub_name, prompt_context)
                    initial_chat.append({"role": "user", "content": log_notes})
                    initial_chat.append({"role": "assistant", "content": ai_response})

                new_log = study_log(
                    user_id=st.session_state.user_id,
                    subject_id=selected_sub_id,
                    duration_minutes=duration_mins,
                    notes=log_notes,
                    ai_chat_history=json.dumps(initial_chat) if initial_chat else None
                )
                db.add(new_log)
                db.commit()
                st.success("Study log saved successfully! Your consistency graph and journal have been updated.")
                st.rerun()

        st.markdown("---")

        # SECTION 2: VIEW AND FILTER PAST LOGS 
        st.subheader("Past Reflection Logs")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            time_filter = st.selectbox(
                "Filter History By Time", 
                ["Last 24 Hours", "Last 7 Days", "Last 1 Month", "Last 3 Months", "All Logs"]
            )
        with col_f2:
            subject_filter_options = ["All Subjects"] + list(subject_options.keys())
            subject_filter = st.selectbox("Filter History By Subject", subject_filter_options)

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
            #subject filter
            logged_sub = db.query(subject).filter(subject.id == log.subject_id).first()
            sub_name_disp = logged_sub.name if logged_sub else "Unknown Subject"
            
            if subject_filter != "All Subjects" and sub_name_disp != subject_filter:
                continue
            #time filter
            if log.created_at:
                try:
                    log_dt = datetime_lib.datetime.strptime(log.created_at, "%Y-%m-%d %H:%M:%S")
                    if threshold is None or log_dt >= threshold:
                        filtered_logs.append((log, log_dt, sub_name_disp))
                except:
                    filtered_logs.append((log, now,sub_name_disp))
        #sort by most recent first
        filtered_logs = sorted(filtered_logs, key=lambda x: x[1], reverse=True)

        if filtered_logs:
            st.write(f"Showing **{len(filtered_logs)}** log entry/entries for *{time_filter}*:")
            for log, log_dt,sub_name_disp in filtered_logs:
                expander_label = f"📘 {sub_name_disp} — ⏱️ {log.duration_minutes} mins — 📅 {log.created_at}"
                
                with st.expander(expander_label, expanded=False):
                    if log.notes:
                        st.info(f"**Reflection / Roadblocks:**\n\n{log.notes}")
                    else:
                        st.caption("No written notes provided for this session.")
                
                    
                    
                    # AI TUTOR THREAD
                    chat_history = json.loads(log.ai_chat_history) if log.ai_chat_history else []

                    if chat_history:
                        st.markdown("---")
                        st.markdown("AI Tutor Thread")
                        for message in chat_history:
                            if message["role"] == "user":
                                st.markdown(f"**You**")
                                st.write(message['content'])
                            else:
                                st.markdown(f"AI Tutor")
                                st.write(message['content'])
                            st.markdown("<hr style='margin: 5px 0px; border-top: 1px solid #ccc;'/>", unsafe_allow_html=True)
                            
                        # Interactive follow-up input for ongoing chat
                        user_reply = st.text_input("Reply to AI Tutor...", key=f"reply_input_{log.id}")
                        if st.button("Send Reply", key=f"send_reply_{log.id}") and user_reply.strip():
                            chat_history.append({"role": "user", "content": user_reply})
                            
                            
                            next_reply = get_ai_tutor_response(sub_name_disp,chat_history)
                            chat_history.append({"role": "assistant", "content": next_reply})
                            
                            log.ai_chat_history = json.dumps(chat_history)
                            db.commit()
                            st.rerun()
                    else:
                        # Option to trigger AI retroactively
                        if st.button("✨ Ask AI About This Log", key=f"trigger_ai_{log.id}"):
                            chat_history = [
                                {"role": "user", "content": log.notes}
                            ]
                            ai_response = get_ai_tutor_response(sub_name_disp,chat_history)
                            chat_history.append({"role": "assistant", "content": ai_response})
                            
                            log.ai_chat_history = json.dumps(chat_history)
                            db.commit()
                            st.rerun()

                    st.markdown("---")
                    
                    # Delete log button
                    if st.button("🗑️ Delete Log Entry", key=f"del_log_{log.id}"):
                        db.delete(log)
                        db.commit()
                        st.success("Study log deleted.")
                        st.rerun()
        else:
            st.info(f"No study logs found for the selected filter ({time_filter}). Start writing logs above to build your history!")
                    

    db.close()