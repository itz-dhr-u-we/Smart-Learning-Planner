import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
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