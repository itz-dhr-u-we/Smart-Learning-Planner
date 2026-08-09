import streamlit as st
import os
import datetime as datetime_lib
from datetime import date
from src.database import SessionLocal, subject, usersubject, topic, Resource
from src.helper import get_resource_suggestion

def update_topic_status(topic_id):
    db = SessionLocal()
    t = db.query(topic).filter(topic.id == topic_id).first()
    if t:
        key = f"covered_{topic_id}"
        if key in st.session_state:
            t.is_covered = st.session_state[key]
            db.commit()
    db.close()

def delete_topic(topic_id):
    db = SessionLocal()
    t = db.query(topic).filter(topic.id == topic_id).first()
    if t:
        db.delete(t)
        db.commit()
    db.close()
def extract_text_from_pdf_robust(file_path, sub_name, topic_name=None):
    """Extracts text via pypdf; if empty (scanned/handwritten), uploads directly to Gemini for multimodal processing."""
    if not file_path or not os.path.exists(file_path):
        return None, "File not found."

    extracted_text = ""
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                extracted_text += t + "\n"
    except Exception:
        pass

    # If pypdf extracted text successfully, use it
    if extracted_text.strip():
        return extracted_text[:12000], "text"

    # Fallback: If text is empty (scanned image or handwritten), use Gemini File API
    try:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key) if api_key else genai.Client()

        # Upload the PDF file directly to Gemini
        with st.spinner("Detected scanned/handwritten PDF. Uploading to Gemini vision engine..."):
            uploaded_file = client.files.upload(file=file_path)

            prompt = f"Extract all text, formulas, notes, and concepts from this document regarding {sub_name}"
            if topic_name:
                prompt += f", specifically focusing on {topic_name}."

            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=[uploaded_file, prompt]
            )
            return response.text, "multimodal"
    except Exception as e:
        return None, str(e)

def render_manage_subjects_tab():
    db = SessionLocal()
    st.title("Manage Your Subjects")

    with st.form("add_subject_form"):
        st.subheader("Add Subject to Catalog")
        sub_name = st.text_input("Subject Name (e.g., Database Management System)")
        category = st.selectbox("Category", ["Theory", "Lab", "Others"])
        credits = st.number_input("Credits", min_value=1, max_value=10, value=4)
        has_exam_date = st.checkbox("Set an Exam Date now?")
        exam_date = st.date_input("Target Exam Date", value=date.today()) if has_exam_date else None
        
        submit_sub = st.form_submit_button("Add Subject")

        if submit_sub and sub_name:
            subj_obj = db.query(subject).filter(subject.name == sub_name).first()
            if not subj_obj:
                subj_obj = subject(name=sub_name, category=category, credits=credits)
                db.add(subj_obj)
                db.commit()
                db.refresh(subj_obj)
            
            if subj_obj and subj_obj.id:
                existing_enrollment = db.query(usersubject).filter(
                    usersubject.user_id == st.session_state.user_id,
                    usersubject.subject_id == subj_obj.id
                ).first()

                if not existing_enrollment:
                    enrollment = usersubject(
                        user_id=st.session_state.user_id, 
                        subject_id=subj_obj.id, 
                        exam_date=str(exam_date) if has_exam_date else None
                    )
                    db.add(enrollment)
                    db.commit()
                    st.success(f"Enrolled in {sub_name} successfully!")
                    st.rerun()
                else:
                    st.warning("You are already enrolled in this subject.")

    st.markdown("---------------------------------")
    st.subheader("Your Enrolled Subjects")
    enrollments = db.query(usersubject).filter(usersubject.user_id == st.session_state.user_id).all()

    if not enrollments:
        st.info("You have not enrolled in any subjects yet.")
    else:
        for enr in enrollments:
            sub = db.query(subject).filter(subject.id == enr.subject_id).first()
            exam_info = f" | Exam Date: {enr.exam_date}" if enr.exam_date else ""
            with st.expander(f"{sub.name} ({sub.category}) - {sub.credits} Credits{exam_info}"):
                
                # --- EDIT SUBJECT FORM ---
                with st.form(f"edit_subject_form_{sub.id}"):
                    st.write("✏️ Edit Subject Details")
                    new_sub_name = st.text_input("Subject Name", value=sub.name, key=f"edit_name_{sub.id}")
                    new_category = st.selectbox("Category", ["Theory", "Lab", "Others"], index=["Theory", "Lab", "Others"].index(sub.category) if sub.category in ["Theory", "Lab", "Others"] else 0, key=f"edit_cat_{sub.id}")
                    new_credits = st.number_input("Credits", min_value=1, max_value=10, value=sub.credits, key=f"edit_cred_{sub.id}")
                    
                    current_date_val = date.today()
                    if enr.exam_date and enr.exam_date != "None":
                        try:
                            current_date_val = datetime_lib.datetime.strptime(enr.exam_date, "%Y-%m-%d").date()
                        except:
                            pass
                        
                    has_exam = st.checkbox("Set/Update Exam Date", value=bool(enr.exam_date and enr.exam_date != "None"), key=f"edit_has_date_{sub.id}")
                    new_exam_date = st.date_input("Target Exam Date", value=current_date_val, key=f"edit_date_{sub.id}")

                    if st.form_submit_button("Save Changes"):
                        sub.name = new_sub_name
                        sub.category = new_category
                        sub.credits = new_credits
                        enr.exam_date = str(new_exam_date) if has_exam else None
                        db.commit()
                        st.success("Subject updated successfully!")
                        st.rerun()

                st.markdown("---")
                
                # --- COURSE RESOURCES & SUMMARIZER HUB ---
                st.markdown("📚 Course Resources & Playlist Tracker")
                
                with st.form(f"add_resource_form_{sub.id}"):
                    res_type = st.selectbox("Resource Type", ["PDF Slides / Notes", "Reference Book / Chapter", "YouTube Playlist"], key=f"res_type_{sub.id}")
                    res_title = st.text_input("Resource Title (e.g., Lecture Notes)", key=f"res_title_{sub.id}")
                    uploaded_file = st.file_uploader("Upload PDF Notes (Optional)", type=["pdf"], key=f"pdf_upload_{sub.id}")
                    res_link_or_path = st.text_input("Alternative YouTube URL or Details", key=f"res_link_{sub.id}")

                    submit_res = st.form_submit_button("Add Resource")
                    if submit_res and res_title:
                        path_to_store = res_link_or_path
                        if uploaded_file is not None:
                            os.makedirs("data/uploads", exist_ok=True)
                            clean_filename = uploaded_file.name.replace(" ", "_")
                            path_to_store = os.path.join("data/uploads", clean_filename)
                            with open(path_to_store, "wb") as f:
                                f.write(uploaded_file.getbuffer())

                        db.add(Resource(subject_id=sub.id, resource_type=res_type, title=res_title, content_path_or_link=path_to_store))
                        db.commit()
                        st.success("Resource added successfully!")
                        st.rerun()

                # Display existing resources with Delete and Summarize options
                subject_resources = db.query(Resource).filter(Resource.subject_id == sub.id).all()
                if subject_resources:
                    st.write("📂 Existing Resources:")
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    upload_dir = os.path.join(base_dir, "..", "data", "uploads")
                    available_pdfs = [f for f in os.listdir(upload_dir) if f.lower().endswith('.pdf')] if os.path.exists(upload_dir) else []

                    for res in subject_resources:
                        col_res1, col_res2, col_res3 = st.columns([0.5, 0.25, 0.25])
                        col_res1.write(f"**[{res.resource_type}]** {res.title}")
                        
                        if col_res3.button("🗑️ Delete", key=f"del_res_{res.id}"):
                            db.delete(res)
                            db.commit()
                            st.success(f"Deleted '{res.title}'")
                            st.rerun()

                        if "PDF" in res.resource_type or (res.content_path_or_link and res.content_path_or_link.endswith('.pdf')):
                            if available_pdfs:
                                selected_file = col_res2.selectbox("Select PDF File", available_pdfs, key=f"select_pdf_{res.id}")
                                if st.button(f"✨ Summarize", key=f"sum_btn_{res.id}"):
                                    with st.spinner("Extracting and summarizing PDF text..."):
                                        target_path = res.content_path_or_link if (res.content_path_or_link and os.path.exists(res.content_path_or_link)) else os.path.join("data", "uploads", selected_file)

                                        content_result, mode = extract_text_from_pdf_robust(target_path, sub.name)
                                        if content_result:
                                            if mode == "text":
                                                summary_result = get_resource_suggestion(sub.name, topic_name=None, pdf_context=content_result)
                                            else:
                                                summary_result = content_result  # Gemini already processed it directly

                                            st.markdown(f"### 📝 Exam Summary")
                                            st.info(summary_result)
                                        else:
                                            st.warning("Could not process this PDF. Ensure it is a valid document file.")
                                        
                
                st.markdown("---")

                # --- TOPIC MANAGEMENT & AI GUIDE ---
                st.markdown("🎯 Topics")
                topics = db.query(topic).filter(topic.subject_id == sub.id).all()
                for t in topics:
                    col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
                    col1.write(f"{t.name}")
                    col2.checkbox("Covered", value=t.is_covered, key=f"covered_{t.id}", on_change=update_topic_status, args=(t.id,))
                    col3.button("Delete", key=f"delete_{t.id}", on_click=delete_topic, args=(t.id,))

                    if st.button(f"Ask AI Guide for '{t.name}'", key=f"ai_help_{t.id}"):
                        with st.spinner("Analyzing lecture notes and consulting knowledge base..."):
                            pdf_texts = ""
                            for r in subject_resources:
                                if r.content_path_or_link:
                                    extracted = extract_text_from_pdf(r.content_path_or_link)
                                    if extracted:
                                        pdf_texts += extracted + "\n"

                            ai_advice = get_resource_suggestion(sub.name, t.name, pdf_context=pdf_texts[:8000] if pdf_texts else None)
                            st.info(ai_advice)

                with st.form(f"add_topic_form_{sub.id}"):
                    new_topic_name = st.text_input("New Topic Name", key=f"new_topic_{sub.id}")
                    if st.form_submit_button("Add Topic") and new_topic_name:
                        db.add(topic(subject_id=sub.id, name=new_topic_name))
                        db.commit()
                        st.success("Topic added successfully!")
                        st.rerun()

    db.close()