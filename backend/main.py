import os
import shutil

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
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