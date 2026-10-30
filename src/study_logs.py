
import streamlit as st
import datetime as datetime_lib
from datetime import timedelta

from src.database import (
    SessionLocal,
    usersubject,
    subject,
    study_log,
    TutorConversation
)

from src.tutor_service import (
    get_or_create_log_conversation,
    get_conversation_history,
    generate_tutor_response
)


def render_study_logs_tab():

    st.title("Study Logs & AI Doubt Tutor")
    
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #F7F4FF, #F4F8FF, #FFF7F2);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    .block-container {
        max-width: 1100px;
        padding-top: 2.2rem;
        padding-bottom: 3rem;
    }

    h1 {
        color: #493D67 !important;
        font-weight: 700 !important;
    }

    h2, h3 {
        color: #574A75 !important;
        font-weight: 650 !important;
    }

    [data-testid="stForm"] {
        background: rgba(255,255,255,0.9);
        border: 1px solid #E7E0F1;
        border-radius: 18px;
        padding: 22px;
    }

    [data-testid="stExpander"] {
        background: rgba(255,255,255,0.9);
        border: 1px solid #E4DDF0;
        border-radius: 15px;
        margin-bottom: 10px;
    }

    [data-testid="stExpander"] summary {
        color: #574A75;
        font-weight: 600;
    }

    [data-testid="stChatMessage"] {
        border-radius: 14px;
    }

    .stTextInput input,
    .stTextArea textarea {
        border-radius: 10px;
        border-color: #DDD5EC;
        background: white;
    }

    [data-testid="stSelectbox"] > div > div {
        border-radius: 10px;
    }

    .stButton > button,
    .stFormSubmitButton > button {
        background: #8E7AB8;
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        padding: 7px 16px;
    }

    .stButton > button:hover,
    .stFormSubmitButton > button:hover {
        background: #75619F;
        color: white;
        border: none;
    }

    [data-testid="stAlert"] {
        border-radius: 12px;
    }

    </style>
    """, unsafe_allow_html=True)

    st.write(
        "Record what you accomplished, track difficulties or roadblocks, "
        "and review your learning history over time."
    )

    user_id = st.session_state.user_id

    db = SessionLocal()

    try:
        user_subjects = db.query(usersubject).filter(
            usersubject.user_id == user_id
        ).all()

        if not user_subjects:
            st.warning(
                "Please enroll in subjects under 'Manage Subjects' "
                "before writing study logs."
            )
            return

        subject_options = {}

        for enrollment in user_subjects:
            sub = db.query(subject).filter(
                subject.id == enrollment.subject_id
            ).first()

            if sub:
                subject_options[sub.name] = sub.id

        with st.form("add_study_log_form"):

            st.subheader("Write a New Log Entry")

            selected_sub_name = st.selectbox(
                "Select Subject",
                list(subject_options.keys())
            )

            selected_sub_id = subject_options[selected_sub_name]

            duration_mins = st.number_input(
                "Time Spent (in minutes)",
                min_value=5,
                max_value=600,
                value=60,
                step=5
            )

            log_notes = st.text_area(
                "Session Reflection & Roadblocks",
                placeholder=(
                    "e.g., Completed Concurrency Control up to 2PL "
                    "protocols. Got stuck on strict vs rigorous "
                    "serializability graphs."
                )
            )

            col_btn1, col_btn2 = st.columns(2)

            save_only = col_btn1.form_submit_button("Save Log Entry")
            save_and_ai = col_btn2.form_submit_button("Save & Ask AI Tutor")

        if save_only or save_and_ai:

            if not log_notes.strip():
                st.warning("Please enter your study reflection first.")

            else:
                new_log = study_log(
                    user_id=user_id,
                    subject_id=selected_sub_id,
                    duration_minutes=duration_mins,
                    notes=log_notes
                )

                db.add(new_log)
                db.commit()
                db.refresh(new_log)

                if save_and_ai:

                    try:
                        conversation_id = get_or_create_log_conversation(
                            user_id,
                            new_log.id
                        )

                        initial_prompt = (
                            f"My study reflection and doubts: {log_notes}\n\n"
                            "Please explain the difficult parts clearly "
                            "and end with a short active-recall question."
                        )

                        generate_tutor_response(
                            user_id,
                            conversation_id,
                            initial_prompt
                        )

                        st.success("Study log saved and AI Tutor conversation started.")

                    except Exception as error:
                        st.error(
                            f"Study log was saved, but the AI response "
                            f"could not be generated: {error}"
                        )

                else:
                    st.success("Study log saved successfully!")

                db.close()
                st.rerun()

        st.markdown("---")


        st.subheader("Past Reflection Logs")

        col_f1, col_f2 = st.columns(2)

        with col_f1:
            time_filter = st.selectbox(
                "Filter History By Time",
                [
                    "Last 24 Hours",
                    "Last 7 Days",
                    "Last 1 Month",
                    "Last 3 Months",
                    "All Logs"
                ]
            )

        with col_f2:
            subject_filter_options = (
                ["All Subjects"] + list(subject_options.keys())
            )

            subject_filter = st.selectbox(
                "Filter History By Subject",
                subject_filter_options
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
            threshold = None

        all_user_logs = db.query(study_log).filter(
            study_log.user_id == user_id
        ).all()

        filtered_logs = []

        for log in all_user_logs:

            logged_sub = db.query(subject).filter(
                subject.id == log.subject_id
            ).first()

            sub_name_disp = (
                logged_sub.name if logged_sub else "Unknown Subject"
            )

            if (
                subject_filter != "All Subjects"
                and sub_name_disp != subject_filter
            ):
                continue

            if log.created_at:
                try:
                    log_dt = datetime_lib.datetime.strptime(
                        log.created_at,
                        "%Y-%m-%d %H:%M:%S"
                    )

                    if threshold is None or log_dt >= threshold:
                        filtered_logs.append(
                            (log, log_dt, sub_name_disp)
                        )

                except ValueError:
                    filtered_logs.append(
                        (log, now, sub_name_disp)
                    )

        filtered_logs.sort(
            key=lambda x: x[1],
            reverse=True
        )

        if filtered_logs:

            st.write(
                f"Showing **{len(filtered_logs)}** log entries "
                f"for *{time_filter}*:"
            )

            for log, log_dt, sub_name_disp in filtered_logs:

                expander_label = (
                    f"📘 {sub_name_disp} — "
                    f"⏱️ {log.duration_minutes} mins — "
                    f"📅 {log.created_at}"
                )

                with st.expander(expander_label):

                    if log.notes:
                        st.info(
                            f"**Reflection / Roadblocks:**\n\n{log.notes}"
                        )
                    else:
                        st.caption(
                            "No written notes provided for this session."
                        )

                    # Check for an existing tutor conversation
                    conversation = db.query(TutorConversation).filter(
                        TutorConversation.user_id == user_id,
                        TutorConversation.study_log_id == log.id
                    ).first()

                    has_old_history = bool(log.ai_chat_history)

                    if conversation or has_old_history:

                        # Retrieves existing conversation or migrates
                        # the old JSON chat history.
                        try:
                            conversation_id = get_or_create_log_conversation(
                                user_id,
                                log.id
                            )

                            chat_history = get_conversation_history(
                                user_id,
                                conversation_id
                            )

                            st.markdown("---")
                            st.markdown("### AI Tutor Conversation")

                            for message in chat_history:

                                role = (
                                    "user"
                                    if message["role"] == "user"
                                    else "assistant"
                                )

                                with st.chat_message(role):
                                    st.markdown(message["content"])

                            user_reply = st.text_input(
                                "Reply to AI Tutor...",
                                key=f"reply_input_{log.id}"
                            )

                            if st.button(
                                "Send Reply",
                                key=f"send_reply_{log.id}"
                            ) and user_reply.strip():

                                try:
                                    with st.spinner("AI Tutor is thinking..."):

                                        response = generate_tutor_response(
                                            user_id,
                                            conversation_id,
                                            user_reply
                                        )

                                    st.rerun()

                                except Exception as error:
                                    st.error(
                                        f"Could not generate response: {error}"
                                    )

                        except Exception as error:
                            st.error(
                                f"Could not load this conversation: {error}"
                            )

                    else:

                        if st.button(
                            "✨ Ask AI About This Log",
                            key=f"trigger_ai_{log.id}"
                        ):

                            try:
                                conversation_id = get_or_create_log_conversation(
                                    user_id,
                                    log.id
                                )

                                initial_prompt = (
                                    f"My study reflection and doubts: "
                                    f"{log.notes}\n\n"
                                    "Please explain the difficult parts "
                                    "clearly and end with a short "
                                    "active-recall question."
                                )

                                with st.spinner("AI Tutor is thinking..."):
                                    generate_tutor_response(
                                        user_id,
                                        conversation_id,
                                        initial_prompt
                                    )

                                st.rerun()

                            except Exception as error:
                                st.error(
                                    f"Could not start AI conversation: {error}"
                                )

                    st.markdown("---")

                    # DELETE LOG
                    if st.button(
                        "🗑️ Delete Log Entry",
                        key=f"del_log_{log.id}"
                    ):

                        # Delete associated conversation first
                        if conversation:
                            db.delete(conversation)

                        db.delete(log)
                        db.commit()

                        st.success("Study log deleted.")
                        st.rerun()

        else:
            st.info(
                f"No study logs found for the selected filter "
                f"({time_filter}). Start writing logs above "
                "to build your history!"
            )

    finally:
        db.close()
