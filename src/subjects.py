import streamlit as st
import os
import datetime as datetime_lib
from datetime import date
from src.database import SessionLocal, subject, usersubject, topic, Resource, PlaylistVideo
from src.helper import get_resource_suggestion

def update_topic_confidence(topic_id, score):
    db = SessionLocal()
    t = db.query(topic).filter(topic.id == topic_id).first()
    if t:
        t.confidence_score = score
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

    if extracted_text.strip():
        return extracted_text[:12000], "text"

    try:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key) if api_key else genai.Client()

        with st.spinner("Detected scanned/handwritten PDF. Uploading to Gemini vision engine..."):
            uploaded_file = client.files.upload(file=file_path)

            prompt = f"Extract all text, formulas, notes, and concepts from this document regarding {sub_name}"
            if topic_name:
                prompt += f", specifically focusing on {topic_name}."

            response = client.models.generate_content(
                model='gemini-2.5-flash',
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
            if not sub:
                continue
            exam_info = f" | Exam Date: {enr.exam_date}" if enr.exam_date else ""
            with st.expander(f"{sub.name} ({sub.category}) - {sub.credits} Credits{exam_info}"):
                
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
                
                # --- TOPIC MANAGEMENT & AI GUIDE ---
                st.markdown("🎯 Topics & Confidence Scale (1-10)")
                topics = db.query(topic).filter(topic.subject_id == sub.id).all()
                if not topics:
                    st.info("No topics added yet. Add topics below to map your syllabus.")
                else:
                    for t in topics:
                        col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
                        col1.write(f"{t.name}")
                        new_score = col2.slider(
                            "Confidence", 
                            min_value=1, 
                            max_value=10, 
                            value=t.confidence_score, 
                            key=f"conf_slider_{t.id}",
                            label_visibility="collapsed"
                        )
                        if new_score != t.confidence_score:
                            update_topic_confidence(t.id, new_score)
                        
                        col2.caption(f"Score: {t.confidence_score}/10")

                        if col3.button("🗑️ Delete", key=f"delete_topic_{t.id}"):
                            delete_topic(t.id)
                            st.success(f"Deleted topic '{t.name}'")
                            st.rerun()

                        if st.button(f"Ask AI Guide for '{t.name}'", key=f"ai_help_{t.id}"):
                            with st.spinner("Analyzing lecture notes and consulting knowledge base..."):
                                subject_resources = db.query(Resource).filter(Resource.subject_id == sub.id).all()
                                
                                pdf_texts = ""
                                for r in subject_resources:
                                    if r.content_path_or_link and r.content_path_or_link.lower().endswith('.pdf'):
                                        extracted, _ = extract_text_from_pdf_robust(r.content_path_or_link, sub.name, t.name)
                                        if extracted:
                                            pdf_texts += extracted + "\n"

                                ai_advice = get_resource_suggestion(sub.name, t.name, pdf_context=pdf_texts[:8000] if pdf_texts else None)
                                st.info(ai_advice)

                with st.form(f"add_topic_form_{sub.id}"):
                    new_topic_name = st.text_input("New Sub-Topic Name", key=f"new_topic_{sub.id}")
                    if st.form_submit_button("Add Topic") and new_topic_name:
                        db.add(topic(subject_id=sub.id, name=new_topic_name, confidence_score=1))
                        db.commit()
                        st.success("Topic added successfully!")
                        st.rerun()
                
                # --- COURSE RESOURCES & SUMMARIZER HUB ---
                st.markdown("📚 Subject Resources & Playlist Tracker")
                
                with st.form(f"add_resource_form_{sub.id}"):
                    res_type = st.selectbox("Resource Type", ["PDF Slides / Notes", "Reference Book / Chapter", "YouTube Playlist"], key=f"res_type_{sub.id}")
                    res_title = st.text_input("Resource Title (e.g., Lecture Notes)", key=f"res_title_{sub.id}")
                    
                    topic_options = {t.name: t.id for t in topics}
                    topic_choices = ["General Subject Resource"] + list(topic_options.keys())
                    selected_topic_choice = st.selectbox("Map to Topic (Optional)", topic_choices, key=f"res_topic_map_{sub.id}")

                    uploaded_file = st.file_uploader("Upload PDF Notes (Optional)", type=["pdf"], key=f"pdf_upload_{sub.id}")
                    res_link_or_path = st.text_input("Alternative YouTube URL or Details", key=f"res_link_{sub.id}")
                    res_conf = st.slider("Initial Resource Confidence Score", 1, 10, 1, key=f"res_conf_{sub.id}")

                    submit_res = st.form_submit_button("Add Resource")
                    if submit_res and res_title:
                        path_to_store = res_link_or_path
                        if uploaded_file is not None:
                            os.makedirs("data/uploads", exist_ok=True)
                            clean_filename = uploaded_file.name.replace(" ", "_")
                            path_to_store = os.path.join("data/uploads", clean_filename)
                            with open(path_to_store, "wb") as f:
                                f.write(uploaded_file.getbuffer())

                        t_id = topic_options.get(selected_topic_choice) if selected_topic_choice != "General Subject Resource" else None

                        new_res = Resource(
                            subject_id=sub.id, 
                            topic_id=t_id,
                            resource_type=res_type, 
                            title=res_title, 
                            content_path_or_link=path_to_store,
                            confidence_score=res_conf
                        )
                        db.add(new_res)
                        db.commit()
                        st.success("Resource added successfully!")
                        st.rerun()

                # Display existing resources with Delete and Summarize options
                subject_resources = db.query(Resource).filter(Resource.subject_id == sub.id).all()
                if subject_resources:
                    st.write("📂 Existing Resources:")
                    
                    for res in subject_resources:
                        col_res1, col_res2, col_res3 = st.columns([0.5, 0.3, 0.2])
                        col_res1.write(f"**[{res.resource_type}]** {res.title} (Conf: {res.confidence_score}/10)")
                        
                        if col_res3.button("🗑️ Delete", key=f"del_res_{res.id}"):
                            db.delete(res)
                            db.commit()
                            st.success(f"Deleted '{res.title}'")
                            st.rerun()

                        if res.content_path_or_link and res.content_path_or_link.endswith('.pdf'):
                            if col_res2.button("✨ Summarize PDF", key=f"sum_pdf_{res.id}"):
                                with st.spinner("Extracting and summarizing PDF text..."):
                                    content_result, mode = extract_text_from_pdf_robust(res.content_path_or_link, sub.name)
                                    if content_result:
                                        summary_result = get_resource_suggestion(sub.name, topic_name=None, pdf_context=content_result)
                                        st.markdown(f"### 📝 Exam Summary")
                                        st.info(summary_result)
                                    else:
                                        st.warning("Could not process this PDF. Ensure it is a valid document file.")

                st.markdown("---")

    db.close()