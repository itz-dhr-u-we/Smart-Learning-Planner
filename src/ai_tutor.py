
import streamlit as st
import os
import re

from src.database import SessionLocal, subject
from src.tutor_service import (
    create_conversation,
    get_user_conversations,
    get_conversation_history,
    generate_tutor_response,
    save_tutor_exchange
)

from src.rag.document_loader import extract_text_from_pdf
from src.rag.text_processor import create_chunks
from src.rag.vector_store import (
    store_chunks,
    get_uploaded_documents
)
from src.rag.rag_service import generate_rag_response

def render_ai_tutor_tab():

    st.title("AI Tutor")
    st.write("Your personal AI learning companion.")
    
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
        padding-top: 2rem;
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

    [data-testid="stChatMessage"] {
        background: rgba(255,255,255,0.85);
        border: 1px solid #E7E0F1;
        border-radius: 15px;
        padding: 12px;
        margin-bottom: 10px;
    }

    [data-testid="stChatInput"] {
        border: 1px solid #DDD5EC;
        border-radius: 14px;
        background: white;
    }

    [data-testid="stFileUploader"] {
        background: rgba(255,255,255,0.85);
        border: 1px dashed #B9A9D5;
        border-radius: 14px;
        padding: 12px;
    }

    [data-testid="stSelectbox"] > div > div {
        border-radius: 10px;
        background: white;
    }

    [data-testid="stRadio"] {
        background: rgba(255,255,255,0.75);
        border-radius: 12px;
        padding: 10px;
    }

    [data-testid="stSidebar"] {
        background: #F0EBF8;
    }

    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #574A75 !important;
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
        border: none;
    }

    [data-testid="stAlert"] {
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

    user_id = st.session_state.get("user_id")

    if not user_id:
        st.warning("Please log in first.")
        return

    # Fetch enrolled subjects
    db = SessionLocal()

    try:
        from src.database import usersubject

        enrollments = db.query(usersubject).filter(
            usersubject.user_id == user_id
        ).all()

        subject_options = {}

        for enrollment in enrollments:
            sub = db.query(subject).filter(
                subject.id == enrollment.subject_id
            ).first()

            if sub:
                subject_options[sub.name] = sub.id

    finally:
        db.close()

    if not subject_options:
        st.warning("Please enroll in at least one subject first.")
        return

    st.sidebar.subheader("Tutor Conversations")

    conversations = get_user_conversations(user_id)

    if st.sidebar.button("＋ New Conversation"):
        st.session_state.tutor_conversation_id = None
        st.session_state.tutor_new_conversation = True
        st.rerun()

    selected_conversation_id = st.session_state.get(
        "tutor_conversation_id"
    )

    is_new_conversation = st.session_state.get(
        "tutor_new_conversation", False
    )

    if conversations and not is_new_conversation:

        conversation_options = {
            f"{conv.title} ({conv.created_at}) - ID {conv.id}": conv.id
            for conv in conversations
            if conv.study_log_id is None
        }

        if conversation_options:

            labels = list(conversation_options.keys())

            selected_label = st.sidebar.selectbox(
                "Previous Conversations",
                labels,
                index=next(
                    (
                        i for i, label in enumerate(labels)
                        if conversation_options[label] == selected_conversation_id
                    ),
                    0
                ),
                key="tutor_history_select"
            )

            chosen_id = conversation_options[selected_label]

            if chosen_id != selected_conversation_id:
                st.session_state.tutor_conversation_id = chosen_id
                st.rerun()

    if not selected_conversation_id:

        st.subheader("Start a New Conversation")

        selected_subject_name = st.selectbox(
            "Select Subject",
            list(subject_options.keys())
        )

        mode = st.selectbox(
            "Learning Mode",
            [
                "Concept Explanation",
                "Doubt Solving",
                "Quiz Generation",
                "Study Guidance"
            ]
        )

        if st.button("Start Conversation"):

            conversation_id = create_conversation(
                user_id=user_id,
                subject_id=subject_options[selected_subject_name],
                learning_mode=mode
            )

            st.session_state.tutor_conversation_id = conversation_id
            st.session_state.tutor_new_conversation = False
            st.rerun()

        return

    # Verify selected conversation belongs to user
    conversation_id = selected_conversation_id

    user_conversations = {
        conv.id: conv
        for conv in conversations
        if conv.study_log_id is None
    }

    if conversation_id not in user_conversations:
        st.session_state.tutor_conversation_id = None
        st.rerun()

    conversation = user_conversations[conversation_id]

    st.subheader(conversation.title)
    st.caption(f"Learning mode: {conversation.learning_mode}")

    conversation_subject_id = conversation.subject_id
    tutor_mode = st.radio(
        "Choose tutoring mode",
        ["Normal AI Tutor", "Ask Uploaded PDF"],
        horizontal=True,
        key=f"tutor_mode_{conversation_id}"
    )
    # PDF upload section
    
    # PDF document management

    st.subheader("Study Material")

    # Fetch previously uploaded PDFs for this subject
    try:
        uploaded_documents = get_uploaded_documents(
            user_id,
            conversation_subject_id
        )
    except Exception as error:
        uploaded_documents = []
        st.error(f"Could not load uploaded documents: {error}")

    selected_document = None

    if uploaded_documents:

        selected_document = st.selectbox(
            "Select an uploaded PDF",
            uploaded_documents,
            key=f"selected_pdf_{conversation_id}"
        )

        st.caption("You can reuse these documents without processing them again.")

    else:
        st.info("No PDFs have been uploaded for this subject yet.")

    # Upload a new PDF
    uploaded_pdf = st.file_uploader(
        "Upload a new PDF",
        type=["pdf"],
        key=f"pdf_upload_{conversation_id}"
    )

    if uploaded_pdf is not None:

        if st.button("Process PDF", key=f"process_pdf_{conversation_id}"):

            try:
                with st.spinner("Processing your PDF..."):

                    extracted_pages = extract_text_from_pdf(uploaded_pdf)
                    chunks = create_chunks(extracted_pages)

                    document_name = re.sub(
                        r"[^a-zA-Z0-9_-]",
                        "_",
                        uploaded_pdf.name
                    )

                    stored_count = store_chunks(
                        chunks=chunks,
                        document_name=document_name,
                        user_id=user_id,
                        subject_id=conversation_subject_id
                    )

                st.success(
                    f"PDF processed successfully! {stored_count} chunks stored."
                )

                st.rerun()

            except Exception as error:
                st.error(f"Could not process PDF: {error}")


    history = get_conversation_history(
        user_id,
        conversation_id
    )

    for message in history:

        role = "user" if message["role"] == "user" else "assistant"

        with st.chat_message(role):
            st.markdown(message["content"])

    # Chat input
    

    if tutor_mode == "Normal AI Tutor":
        placeholder = "Ask your AI Tutor..."
    else:
        placeholder = "Ask a question about your uploaded PDF..."

    user_message = st.chat_input(placeholder)

    if user_message:

        try:
            with st.spinner("AI Tutor is thinking..."):

                if tutor_mode == "Normal AI Tutor":

                    # This function already saves both messages.
                    response = generate_tutor_response(
                        user_id,
                        conversation_id,
                        user_message
                    )

                else:
                    document_name = selected_document

                    if not document_name:
                        st.error("Please select or upload a PDF first.")
                        return

                   

                    response = generate_rag_response(
                        question=user_message,
                        user_id=user_id,
                        subject_id=conversation_subject_id,
                        document_name=document_name
                    )

                    # RAG service does not save messages itself.
                    save_tutor_exchange(
                        user_id,
                        conversation_id,
                        user_message,
                        response
                    )

            st.rerun()

        except Exception as error:
            st.error(f"Could not generate response: {error}")
