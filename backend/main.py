import os
import shutil
import json

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from rag import process_pdf, search_documents


# --------------------------------------------------
# 1. Initialize FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="Document Intelligence Portal",
    description="Search and retrieve information from PDF documents.",
    version="1.0.0",
)


# --------------------------------------------------
# 2. Configure CORS for React frontend
# --------------------------------------------------

FRONTEND_URL = os.getenv("FRONTEND_URL", "")

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

if FRONTEND_URL:
    ALLOWED_ORIGINS.append(FRONTEND_URL.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# 3. Configure documents directory
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCUMENTS_DIR = os.path.join(BASE_DIR, "documents")

os.makedirs(DOCUMENTS_DIR, exist_ok=True)


# Serve original PDFs to the frontend.
# Example: /documents/tata_tender.pdf

app.mount(
    "/documents",
    StaticFiles(directory=DOCUMENTS_DIR),
    name="documents",
)

# Serve reconstructed page previews and OCR data.
RECONSTRUCTED_DIR = os.path.join(
    BASE_DIR,
    "reconstructed_documents",
)

app.mount(
    "/reconstructed",
    StaticFiles(directory=RECONSTRUCTED_DIR),
    name="reconstructed",
)

# Automatically index the supplied PDFs when the backend starts.
@app.on_event("startup")
def index_existing_documents():
    for filename in ["company_document.pdf", "tata_tender.pdf"]:
        file_path = os.path.join(DOCUMENTS_DIR, filename)

        if os.path.isfile(file_path):
            try:
                result = process_pdf(file_path)
                print(f"Indexed {filename}: {result}")
            except Exception as error:
                print(f"Failed to index {filename}: {error}")
            
# --------------------------------------------------
# 4. Home endpoint
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Document Intelligence Portal API is running!"
    }


# --------------------------------------------------
# 5. Health-check endpoint
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }

# --------------------------------------------------
# 6. Retrieve OCR data for a specific PDF page
# --------------------------------------------------

@app.get("/page-data/{filename}/{page_number}")
def get_page_data(filename: str, page_number: int):

    safe_filename = os.path.basename(filename)

    if not safe_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF filename.",
        )

    if page_number < 1:
        raise HTTPException(
            status_code=400,
            detail="Page number must be at least 1.",
        )

    document_name = os.path.splitext(safe_filename)[0]

    json_path = os.path.join(
        BASE_DIR,
        "reconstructed_documents",
        document_name,
        "document_data.json",
    )

    if not os.path.isfile(json_path):
        raise HTTPException(
            status_code=404,
            detail="Reconstructed document data not found.",
        )

    try:
        with open(json_path, "r", encoding="utf-8") as file:
            pages = json.load(file)

        for page in pages:
            if page.get("page_number") == page_number:
                return page

        raise HTTPException(
            status_code=404,
            detail="Page not found.",
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read page data: {str(error)}",
        ) from error
# --------------------------------------------------
# 6. Upload and index a PDF document
# --------------------------------------------------

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF file.",
        )

    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(DOCUMENTS_DIR, safe_filename)

    try:
        # Save the uploaded PDF.
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract text, create chunks, generate embeddings,
        # and store the indexed chunks in ChromaDB.
        result = process_pdf(file_path)

        # Propagate processing errors instead of reporting success.
        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(
                status_code=422,
                detail=result["error"],
            )

        return result

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"PDF processing failed: {str(error)}",
        ) from error

    finally:
        await file.close()


# --------------------------------------------------
# 7. Semantic search endpoint
# --------------------------------------------------

@app.get("/search")
def search_endpoint(q: str, top_k: int = 5):

    if not q.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty.",
        )

    if not 1 <= top_k <= 20:
        raise HTTPException(
            status_code=400,
            detail="top_k must be between 1 and 20.",
        )

    try:
        # Use the shared search function from rag.py.
        return search_documents(q, top_k=top_k)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Document search failed: {str(error)}",
        ) from error