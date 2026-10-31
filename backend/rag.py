import os
import re
import html
from io import BytesIO

import pymupdf
import pytesseract
import chromadb

from PIL import Image

from sklearn.feature_extraction.text import HashingVectorizer

from langchain_text_splitters import RecursiveCharacterTextSplitter

# --------------------------------------------------
# 1. TESSERACT OCR CONFIGURATION
# --------------------------------------------------

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# --------------------------------------------------
# 2. DIRECTORY CONFIGURATION
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DOCUMENTS_DIR = os.path.join(BASE_DIR, "documents")
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
os.makedirs(CHROMA_DIR, exist_ok=True)


# --------------------------------------------------
# 3. CHROMADB CONFIGURATION
# --------------------------------------------------

chroma_client = chromadb.PersistentClient(
    path=CHROMA_DIR
)

collection = chroma_client.get_or_create_collection(
    name="documents"
)

# --------------------------------------------------
# 4. LIGHTWEIGHT TEXT VECTORIZER
# --------------------------------------------------

vectorizer = HashingVectorizer(
    n_features=384,
    alternate_sign=False,
    norm="l2"
)


# --------------------------------------------------
# 5. TEXT CHUNKING CONFIGURATION
# --------------------------------------------------

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    separators=["\n\n", "\n", ". ", " ", ""],
    length_function=len,
)


# --------------------------------------------------
# 6. TEXT CLEANING
# --------------------------------------------------

def clean_text(text: str) -> str:
    """
    Clean extracted PDF text while preserving
    useful line breaks and paragraph structure.
    """

    text = html.unescape(text or "")
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize spaces and tabs without removing line breaks.
    text = re.sub(r"[ \t]+", " ", text)

    # Remove spaces around line breaks.
    text = re.sub(r" *\n *", "\n", text)

    # Collapse excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# --------------------------------------------------
# 7. PDF TEXT EXTRACTION AND OCR
# --------------------------------------------------


def extract_page_text(page) -> str:
    """
    Extract complete PDF page text.
    Use OCR only when native PDF text is unavailable.
    """

    # 1. Extract all native PDF text first.
    text = page.get_text("text", sort=True).strip()

    if text:
        return text

    # 2. Use OCR only for scanned/image-based pages.
    pix = page.get_pixmap(dpi=300, alpha=False)
    image = Image.open(BytesIO(pix.tobytes("png")))

    text = pytesseract.image_to_string(
        image,
        lang="eng",
        config="--psm 3",
    )

    return text.strip()

# --------------------------------------------------
# 8. REMOVE OLD CHUNKS FOR A DOCUMENT
# --------------------------------------------------

def remove_document_chunks(document_name: str) -> None:
    """
    Remove previously indexed chunks for this document.

    This prevents obsolete chunks from remaining when
    a document is re-indexed and its chunk count changes.
    """

    collection.delete(
        where={"document": document_name}
    )


# --------------------------------------------------
# 9. PROCESS PDF AND STORE CHUNKS IN CHROMADB
# --------------------------------------------------

def process_pdf(file_path: str) -> dict:
    """
    Extract PDF text page by page, clean it, split it
    into chunks, generate embeddings, and store them
    in ChromaDB with document and page metadata.
    """

    if not os.path.isfile(file_path):
        raise FileNotFoundError(
            f"PDF file not found: {file_path}"
        )

    if not file_path.lower().endswith(".pdf"):
        raise ValueError(
            "Only PDF files can be processed."
        )

    document_name = os.path.basename(file_path)

    chunks = []
    metadatas = []
    ids = []

    # Open and process the PDF.
    with pymupdf.open(file_path) as pdf_document:

        for page_number, page in enumerate(
            pdf_document,
            start=1
        ):

            # Extract and clean page text.
            page_text = clean_text(
                extract_page_text(page)
            )

            if not page_text:
                continue

            # Split page text into manageable chunks.
            page_chunks = text_splitter.split_text(
                page_text
            )

            for chunk_index, chunk in enumerate(
                page_chunks
            ):

                chunks.append(chunk)

                metadatas.append({
                    "document": document_name,
                    "page": page_number
                })

                ids.append(
                    f"{document_name}_page{page_number}_chunk{chunk_index}"
                )

    # Do not delete existing indexed data if extraction
    # produced no text.
    if not chunks:
        return {
            "message": (
                "No text could be extracted from the PDF, "
                "even after attempting OCR. Existing indexed "
                "chunks have been preserved."
            ),
            "document": document_name,
            "chunks_created": 0
        }

    # Generate embeddings before replacing old records.
    embeddings = vectorizer.transform(chunks).toarray().tolist()

    # Remove obsolete records for this document.
    remove_document_chunks(document_name)

    # Store the newly generated chunks and embeddings.
    collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return {
        "message": "PDF processed successfully.",
        "document": document_name,
        "pages_processed": len(set(
            metadata["page"] for metadata in metadatas
        )),
        "chunks_created": len(chunks)
    }


# --------------------------------------------------
# 10. SEARCH DOCUMENTS
# --------------------------------------------------

def search_documents(query: str, top_k: int = 5) -> dict:
    """
    Search indexed PDF chunks using semantic similarity.
    Return the matching text, document, page, and distance.
    """

    query = query.strip()

    if not query:
        raise ValueError("Search query cannot be empty.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    total_chunks = collection.count()

    if total_chunks == 0:
        return {
            "query": query,
            "total_results": 0,
            "results": []
        }

    query_embedding = vectorizer.transform([query]).toarray().tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, total_chunks),
        include=["documents", "metadatas", "distances"]
    )

    matches = []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for text, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):

        matches.append({
            "text": text,
            "document": metadata.get("document", ""),
            "page": metadata.get("page", 0),
            "distance": distance
        })

    return {
        "query": query,
        "total_results": len(matches),
        "results": matches
    }
