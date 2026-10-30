
from langchain_text_splitters import RecursiveCharacterTextSplitter


def create_chunks(extracted_pages):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""]
    )

    chunks = []

    for page_data in extracted_pages:

        page_text = page_data["text"]
        page_number = page_data["page"]

        page_chunks = splitter.split_text(page_text)

        for chunk in page_chunks:

            chunks.append({
                "text": chunk,
                "page": page_number
            })

    return chunks
