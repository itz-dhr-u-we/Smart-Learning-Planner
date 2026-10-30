import streamlit as st
from src.database import init_db
from src.auth import render_auth_page
from src.dashboard import render_dashboard_tab
from src.subjects import render_manage_subjects_tab
from src.study_logs import render_study_logs_tab
from src.ai_auditor import render_ai_auditor_tab
from src.ai_tutor import render_ai_tutor_tab
init_db()
st.set_page_config(page_title="Smart Learning Planner", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None

def main_app():
    st.sidebar.title(f"Welcome, {st.session_state.username}!")
    menu = st.sidebar.radio("Navigation", ["Dashboard", "Manage Subjects", "Study Logs", "AI Review", "AI Tutor"])

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.rerun()

    if menu == "Dashboard":
        render_dashboard_tab()
    elif menu == "Manage Subjects":
        render_manage_subjects_tab()
    elif menu == "Study Logs":
        render_study_logs_tab()
    elif menu == "AI Review":
        render_ai_auditor_tab()
    elif menu == "AI Tutor":
        render_ai_tutor_tab()

if not st.session_state.logged_in:
    render_auth_page()
else:
    main_app()