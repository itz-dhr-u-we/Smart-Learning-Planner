import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
def get_ai_tutor_response(subject_name, chat_history_list):
    """
    Generates a concise, conversational tutor response tailored for study log chats.
    """
    client = genai.Client()
    
    # Format the ongoing conversation history cleanly for the model
    formatted_history = ""
    for msg in chat_history_list:
        if isinstance(msg, dict):
            role = "Student" if msg.get("role") == "user" else "AI Tutor"
            content = msg.get("content", "")
        else:
            role = "Student"
            content = str(msg)
        formatted_history += f"{role}: {content}\n"

    prompt = f"""
    You are an expert, concise engineering study companion helping a student with '{subject_name}'.
    
    Here is the ongoing conversation history:
    {formatted_history}
    
    INSTRUCTIONS:
    - Keep your response brief, conversational, and direct (max 2-3 short paragraphs).
    - Answer the student's exact question or address their specific roadblock immediately (e.g., if they ask about computer network handshakes vs architecture tiers, give a crisp, accurate comparison).
    - Do NOT generate massive markdown study guides, long outlines, or textbook summaries.
    - End with a short, engaging follow-up question or quick check to test their understanding.
    """

    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"AI Tutor is temporarily unavailable. (Error: {str(e)})"


def get_resource_suggestion(subject_name, topic_name,pdf_context=None):
    """
    Uses Gemini to dynamically generate targeted study recommendations, 
    standard reference books, and key concepts for any engineering topic.
    """
    # Initialize the Gemini client (picks up GEMINI_API_KEY from environment variables)
    client = genai.Client()
    if pdf_context and len(pdf_context.strip()) > 50:
        prompt = f"""
        You are an expert exam preparation coach. 
        An engineering student is preparing for an exam in '{subject_name}'. 
        Below is the text extracted from their uploaded study material or lecture notes:
        
        -----------------
        {pdf_context}
        -----------------
        
        Based EXCLUSIVELY on the text provided above, generate a comprehensive exam review containing:
        1. **Core Topics Breakdown**: List all the major topics and subtopics covered in this document.
        2. **Comprehensive Summary**: Provide a clear, high-yield summary of the vital concepts, definitions, and principles needed to master the material before going into the exam.
        3. **Key Formulas/Pointers**: Highlight any crucial technical points, formulas, or rules mentioned.
        
        Keep it structured, thorough, and optimized for last-minute exam revision.
        """
    else:
        prompt = f"""
        You are an expert computer science academic advisor. 
        A student is studying '{subject_name}' on the topic '{topic_name}'. 
        (Note: No PDF notes were uploaded for this topic, so use standard curriculum knowledge).
        
        Provide concise, high-value study guidance containing standard textbooks, core concepts, and study strategies.
        """

    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"Could not generate AI suggestions at the moment. Please check your API key configuration. (Error: {str(e)})"