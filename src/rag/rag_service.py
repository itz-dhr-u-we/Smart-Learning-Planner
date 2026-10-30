
from langchain_google_genai import ChatGoogleGenerativeAI
from src.rag.vector_store import retrieve_relevant_chunks
from dotenv import load_dotenv
import os

load_dotenv()


def generate_rag_response(
    question,
    user_id,
    subject_id=None,
    document_name=None
):

    chunks = retrieve_relevant_chunks(
        question=question,
        user_id=user_id,
        subject_id=subject_id,
        document_name=document_name,
        k=3
    )

    if not chunks:
        return "I could not find relevant information in your uploaded documents."

    context = ""

    for chunk in chunks:
        context += (
            f"\nPage {chunk['page']}:\n"
            f"{chunk['text']}\n"
        )

    prompt = f"""
    You are a helpful study assistant.

    Answer the student's question using the provided document context.

    Instructions:
    - Base your answer on the given context.
    - Do not make up information.
    - If the answer is not available in the context, say so.
    - Mention relevant page numbers.
    - Explain concepts in simple language.

    Document Context:
    {context}

    Student Question:
    {question}
    """

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY not found.")

    model = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        google_api_key=api_key
    )

    response = model.invoke(prompt)

    #Extract response
    if isinstance(response.content, str):
        return response.content

    if isinstance(response.content, list):
        return "\n".join(
            block.get("text", "")
            for block in response.content
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()

    return str(response.content)
