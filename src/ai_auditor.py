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
        if log.timestamp:
            try:
                log_dt = datetime.strptime(log.timestamp, "%Y-%m-%d %H:%M:%S")
                sub = db.query(subject).filter(subject.id == log.subject_id).first()
                sub_name = sub.name if sub else "Unknown"
                
                # Strict 7-day filter for both global view and subject-specific view
                if log_dt >= seven_days_ago:
                    if selected_target == "All Subjects (Weekly Overview)":
                        filtered_logs.append({"subject": sub_name, "duration": log.duration_minutes, "date": log.timestamp, "notes": log.notes})
                    else:
                        if sub_name == selected_target:
                            filtered_logs.append({"subject": sub_name, "duration": log.duration_minutes, "date": log.timestamp, "notes": log.notes})
            except:
                pass

    if not filtered_logs:
        st.info(f"No study logs found for '{selected_target}' in the past 7 days. Add logs in the 'Study Logs' tab to enable AI reviews!")
    else:
        st.write(f"Found **{len(filtered_logs)}** relevant session(s) from the past 7 days for analysis.")
        
        if st.button(f"Generate AI Review for {selected_target}"):
            with st.spinner("Analyzing study patterns and technical roadblocks..."):
                log_summary_text = ""
                for item in filtered_logs:
                    log_summary_text += f"- **Subject:** {item['subject']} | **Time:** {item['duration']} mins | **Date:** {item['date']}\n  **Reflection/Notes:** {item['notes']}\n\n"

                if selected_target == "All Subjects (Weekly Overview)":
                    prompt = f"""
                    You are an expert AI academic mentor for an engineering student. Analyze these past 7 days of study logs:
                    {log_summary_text}
                    Provide: 
                    1. Consistency & Pacing Summary, 
                    2. Recurring Bottlenecks & Weaknesses, 
                    3. Actionable Plan for Next Week.
                    """
                else:
                    prompt = f"""
                    You are an expert technical tutor specializing in {selected_target}. Analyze the student's history and roadblocks for this specific subject over the past 7 days:
                    {log_summary_text}
                    Provide: 
                    1. Mastery Progress Assessment, 
                    2. Deep Dive into Specific Roadblocks/Difficulties noted, 
                    3. Targeted Revision Strategy for this subject.
                    """

                try:
                    # Initialize client using the official google-genai library
                    api_key = os.environ.get("GEMINI_API_KEY")
                    client = genai.Client(api_key=api_key) if api_key else genai.Client()
                    
                    response = client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=prompt,
                    )
                    
                    st.subheader(f"AI Insights: {selected_target}")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Error generating AI review. Ensure your GEMINI_API_KEY environment variable is set properly. Details: {e}")

    db.close()