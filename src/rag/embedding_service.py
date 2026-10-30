
import os

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()


def get_embedding_model():

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY not found.")

    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=api_key
    )


def generate_embeddings(chunks):

    embedding_model = get_embedding_model()

    texts = [chunk["text"] for chunk in chunks]

    vectors = embedding_model.embed_documents(texts)

    return vectors
