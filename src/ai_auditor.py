import streamlit as st
import os
from datetime import datetime, timedelta
from google import genai
from src.database import SessionLocal, study_log, subject, usersubject

def render_ai_auditor_tab():
    st.title("🤖 AI Study Audit & Mentorship")
    st.write("Get AI-powered insights across your entire week or zoom in on a specific subject's roadblocks.")

    db = SessionLocal()
    user_id = st.session_state.get("user_id")
    
    if not user_id:
        st.warning("Please log in first.")
        db.close()
        return
    

    # Fetch user's enrolled subjects for the dropdown filter
    enrollments = db.query(usersubject).filter(usersubject.user_id == user_id).all()
    if not enrollments:
        st.warning("Please enroll in subjects first.")
        db.close()
        return
        
    subject_names = ["All Subjects (Weekly Overview)"]
    
    for enr in enrollments:
        sub = db.query(subject).filter(subject.id == enr.subject_id).first()
        if sub:
            subject_names.append(sub.name)

    # Selection mode: Global vs Subject-specific
    selected_target = st.selectbox("Select Review Scope", subject_names)

    # Fetch logs
    logs = db.query(study_log).filter(study_log.user_id == user_id).all()
    
    filtered_logs = []
    seven_days_ago = datetime.now() - timedelta(days=7)

    for log in logs:
        
        sub = db.query(subject).filter(subject.id == log.subject_id).first()
        sub_name = sub.name if sub else "Unknown"

        is_recent = False
        if log.created_at:
            parsed = False
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    log_dt = datetime.strptime(log.created_at.strip(), fmt)
                    parsed = True
                    #if created with 7 days or created today,include it
                    if log_dt >= seven_days_ago:
                        is_recent = True 
                    break
                except ValueError:
                    continue
            #if parsing fails,include it anyway so data isnt lost silently
            if not parsed:
                is_recent = True
        else:
            is_recent = True

        # Strict 7-day filter for both global view and subject-specific view
        if is_recent:
            if selected_target == "All Subjects (Weekly Overview)":
                filtered_logs.append({"subject": sub_name, "duration": log.duration_minutes, "date": log.created_at, "notes": log.notes})
            else:
                if sub_name == selected_target:
                    filtered_logs.append({"subject": sub_name, "duration": log.duration_minutes, "date": log.created_at, "notes": log.notes})
        

    if not filtered_logs:
        st.info(f"No study logs found for '{selected_target}' in the past 7 days. Add logs in the 'Study Logs' tab to enable AI reviews!")
    else:
        st.write(f"Found **{len(filtered_logs)}** relevant session(s) from the past 7 days for analysis.")
        
        if st.button(f"Generate AI Review for {selected_target}"):
            with st.spinner("Analyzing study patterns and technical roadblocks..."):
                log_summary_text = ""
                for item in filtered_logs:
                    log_summary_text += f"- **Subject:** {item['subject']} | **Time:** {item['duration']} mins | **Date:** {item['date']}\n  **Reflection/Notes:** {item['notes']}\n\n"

                prompt = f"""
                You are an expert academic auditor. 
                Below is the complete collection of the student's study logs and journal notes for '{selected_target}' over the past 7 days:
                {log_summary_text}
                Synthesize all of these logs into **one single, unified overview** (do not separate them by individual session entries). 
                Provide a clean breakdown using only these bullet points:
                1. *Overall Activity & Accomplishments*: A consolidated summary of what was covered, studied, or progressed across all sessions.
                2. *Roadblocks & Difficulties Faced*: A consolidated list of all specific concepts, topics, or doubts where the student got stuck.
                3. *Important Information / Key Takeaways*: Any critical details, formulas, definitions, or technical pointers noted down across the logs.
                Keep it concise, well-formatted, and completely focused on synthesizing the logs together.
                """
                try:
                    # Initialize client using the official google-genai library
                    api_key = os.environ.get("GEMINI_API_KEY")
                    client = genai.Client(api_key=api_key) if api_key else genai.Client()
                    response = client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=prompt,
                    )
                    st.subheader(f"7-Day AI Insights: {selected_target}")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Error generating AI review. Ensure your GEMINI_API_KEY environment variable is set properly. Details: {e}")

    db.close()