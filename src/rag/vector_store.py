
import os

from dotenv import load_dotenv
from langchain_postgres import PGVector
from sqlalchemy import text

from src.database import engine
from src.rag.embedding_service import get_embedding_model

load_dotenv()

COLLECTION_NAME = "study_materials"


def get_vector_store():

    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        raise ValueError("DATABASE_URL not found.")

    # LangChain PostgreSQL integration uses psycopg 3
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1
        )

    embedding_model = get_embedding_model()

    vector_store = PGVector(
        embeddings=embedding_model,
        collection_name=COLLECTION_NAME,
        connection=db_url,
        use_jsonb=True
    )

    return vector_store


def store_chunks(chunks, document_name, user_id, subject_id):

    vector_store = get_vector_store()

    texts = []
    metadatas = []
    ids = []

    for index, chunk in enumerate(chunks):

        texts.append(chunk["text"])

        metadatas.append({
            "page": chunk["page"],
            "document_name": document_name,
            "user_id": str(user_id),
            "subject_id": str(subject_id)
        })

        ids.append(
            f"{user_id}_{subject_id}_{document_name}_{index}"
        )

    vector_store.add_texts(
        texts=texts,
        metadatas=metadatas,
        ids=ids
    )

    return len(texts)


def retrieve_relevant_chunks(
    question,
    user_id,
    subject_id=None,
    document_name=None,
    k=3
):

    vector_store = get_vector_store()

    conditions = [
        {"user_id": {"$eq": str(user_id)}}
    ]

    if subject_id is not None:
        conditions.append(
            {"subject_id": {"$eq": str(subject_id)}}
        )

    if document_name:
        conditions.append(
            {"document_name": {"$eq": document_name}}
        )

    search_filter = conditions[0]

    if len(conditions) > 1:
        search_filter = {"$and": conditions}

    results = vector_store.similarity_search(
        query=question,
        k=k,
        filter=search_filter
    )

    retrieved_chunks = []

    for result in results:

        retrieved_chunks.append({
            "text": result.page_content,
            "page": result.metadata.get("page"),
            "document_name": result.metadata.get("document_name")
        })

    return retrieved_chunks


def get_uploaded_documents(user_id, subject_id):

    query = text("""
        SELECT DISTINCT e.cmetadata ->> 'document_name'
        FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c
            ON e.collection_id = c.uuid
        WHERE c.name = :collection_name
          AND e.cmetadata ->> 'user_id' = :user_id
          AND e.cmetadata ->> 'subject_id' = :subject_id
          AND e.cmetadata ? 'document_name'
    """)

    with engine.connect() as connection:

        results = connection.execute(
            query,
            {
                "collection_name": COLLECTION_NAME,
                "user_id": str(user_id),
                "subject_id": str(subject_id)
            }
        )

        documents = [
            row[0] for row in results if row[0]
        ]

    return sorted(documents)
