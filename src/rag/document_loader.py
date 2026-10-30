
from pypdf import PdfReader
from io import BytesIO


def extract_text_from_pdf(pdf_file):

    try:
        pdf_bytes = pdf_file.getvalue()

        reader = PdfReader(BytesIO(pdf_bytes))

        extracted_pages = []

        for page_number, page in enumerate(reader.pages, start=1):

            text = page.extract_text()

            if text and text.strip():
                extracted_pages.append({
                    "page": page_number,
                    "text": text.strip()
                })

        if not extracted_pages:
            raise ValueError(
                "No readable text found in this PDF. "
                "It may be a scanned document."
            )

        return extracted_pages

    except Exception as error:
        raise ValueError(f"PDF extraction failed: {error}")
