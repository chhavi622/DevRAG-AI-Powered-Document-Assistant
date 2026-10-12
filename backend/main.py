from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from dotenv import load_dotenv
from groq import Groq
import chromadb
import os
import shutil
import re


# ============================================================
# 1. BASE DIRECTORY + ENVIRONMENT
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ENV_FILE = os.path.join(BASE_DIR, ".env")

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if GROQ_API_KEY:
    GROQ_API_KEY = GROQ_API_KEY.strip()


# ============================================================
# 2. GROQ KEY STATUS
# ============================================================

if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY is missing")
    print(f"Check this file: {ENV_FILE}")

elif GROQ_API_KEY == "YOUR_GROQ_API_KEY":
    print("❌ Replace YOUR_GROQ_API_KEY with your real Groq API key")

else:
    print("✅ GROQ API key loaded")
    print("Key prefix:", GROQ_API_KEY[:8])


# ============================================================
# 3. FASTAPI
# ============================================================

app = FastAPI(
    title="DevRAG API",
    description="AI-powered PDF Question Answering System",
    version="2.0.0"
)
# ============================================================
# 4. CORS
# ============================================================

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    os.getenv("FRONTEND_URL", "").rstrip("/")
]

origins = [origin for origin in origins if origin]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ============================================================
# 5. DIRECTORIES
# ============================================================

UPLOAD_DIR = os.path.join(
    BASE_DIR,
    "uploads"
)

CHROMA_DIR = os.path.join(
    BASE_DIR,
    "chroma_db"
)

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)

os.makedirs(
    CHROMA_DIR,
    exist_ok=True
)


# ============================================================
# 6. CHROMADB
# ============================================================

chroma_client = chromadb.PersistentClient(
    path=CHROMA_DIR
)

collection = chroma_client.get_or_create_collection(
    name="devrag_documents"
)


# ============================================================
# 7. GROQ CLIENT
# ============================================================

groq_client = None

if GROQ_API_KEY:
    groq_client = Groq(
        api_key=GROQ_API_KEY
    )


# ============================================================
# 8. HOME
# ============================================================

@app.get("/")
def home():

    return {
        "success": True,
        "message": "DevRAG Backend is running",
        "version": "2.0.0"
    }


# ============================================================
# 9. HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "success": True,
        "status": "healthy",
        "groq_configured": bool(GROQ_API_KEY),
        "documents": collection.count()
    }


# ============================================================
# 10. CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = text.replace(
        "\x00",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# 11. CREATE TEXT CHUNKS
# ============================================================

def create_chunks(
    text,
    chunk_size=800,
    overlap=100
):

    chunks = []

    start = 0

    step = chunk_size - overlap

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += step

    return chunks


# ============================================================
# 12. UPLOAD PDF
# ============================================================

@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...)
):

    try:

        # ----------------------------------------------------
        # Validate filename
        # ----------------------------------------------------

        if not file.filename:

            return {
                "success": False,
                "message": "No file selected"
            }


        # ----------------------------------------------------
        # Validate PDF
        # ----------------------------------------------------

        if not file.filename.lower().endswith(".pdf"):

            return {
                "success": False,
                "message": "Only PDF files are allowed"
            }


        # ----------------------------------------------------
        # Safe filename
        # ----------------------------------------------------

        safe_filename = re.sub(
            r"[^a-zA-Z0-9._-]",
            "_",
            file.filename
        )


        # ----------------------------------------------------
        # File path
        # ----------------------------------------------------

        file_path = os.path.join(
            UPLOAD_DIR,
            safe_filename
        )


        # ----------------------------------------------------
        # Save file
        # ----------------------------------------------------

        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )


        # ----------------------------------------------------
        # Read PDF
        # ----------------------------------------------------

        reader = PdfReader(
            file_path
        )

        page_count = len(
            reader.pages
        )

        full_text = ""


        # ----------------------------------------------------
        # Extract text
        # ----------------------------------------------------

        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:

                full_text += (
                    page_text + "\n"
                )


        full_text = clean_text(
            full_text
        )


        # ----------------------------------------------------
        # Empty PDF check
        # ----------------------------------------------------

        if not full_text:

            return {
                "success": False,
                "message": (
                    "Could not extract text from this PDF. "
                    "The PDF may contain scanned images."
                )
            }


        # ----------------------------------------------------
        # Create chunks
        # ----------------------------------------------------

        chunks = create_chunks(
            full_text,
            chunk_size=800,
            overlap=100
        )


        # ----------------------------------------------------
        # Delete previous chunks
        # ----------------------------------------------------

        try:

            old_data = collection.get(
                where={
                    "source": safe_filename
                }
            )

            old_ids = old_data.get(
                "ids",
                []
            )

            if old_ids:

                collection.delete(
                    ids=old_ids
                )

        except Exception as delete_error:

            print(
                "Old chunk delete warning:",
                delete_error
            )


        # ----------------------------------------------------
        # Prepare ChromaDB data
        # ----------------------------------------------------

        ids = []

        documents = []

        metadatas = []


        for index, chunk in enumerate(chunks):

            chunk_id = (
                f"{safe_filename}_{index}"
            )

            ids.append(
                chunk_id
            )

            documents.append(
                chunk
            )

            metadatas.append(
                {
                    "source": safe_filename,
                    "chunk": index
                }
            )


        # ----------------------------------------------------
        # Store in ChromaDB
        # ----------------------------------------------------

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )


        # ----------------------------------------------------
        # Response
        # ----------------------------------------------------

        return {

            "success": True,

            "message": (
                "PDF uploaded and processed successfully"
            ),

            "filename": safe_filename,

            "pages": page_count,

            "characters": len(full_text),

            "chunks": len(chunks)
        }


    except Exception as e:

        print(
            "PDF ERROR:",
            str(e)
        )

        return {

            "success": False,

            "message": (
                f"PDF processing failed: {str(e)}"
            )
        }


# ============================================================
# 13. SEARCH
# ============================================================

@app.get("/search")
def search_documents(
    q: str
):

    try:

        query = q.strip()


        if not query:

            return {

                "success": False,

                "message": (
                    "Search query is required"
                )
            }


        document_count = collection.count()


        if document_count == 0:

            return {

                "success": False,

                "message": (
                    "No documents uploaded"
                )
            }


        # ----------------------------------------------------
        # ChromaDB search
        # ----------------------------------------------------

        results = collection.query(

            query_texts=[
                query
            ],

            n_results=min(
                3,
                document_count
            )
        )


        documents = results.get(
            "documents",
            [[]]
        )[0]


        metadatas = results.get(
            "metadatas",
            [[]]
        )[0]


        response = []


        for document, metadata in zip(
            documents,
            metadatas
        ):

            response.append(
                {
                    "text": document,

                    "source": metadata.get(
                        "source",
                        "Unknown"
                    ),

                    "chunk": metadata.get(
                        "chunk",
                        0
                    )
                }
            )


        return {

            "success": True,

            "query": query,

            "results": response
        }


    except Exception as e:

        print(
            "SEARCH ERROR:",
            str(e)
        )

        return {

            "success": False,

            "message": (
                f"Search failed: {str(e)}"
            )
        }


# ============================================================
# 14. ASK AI
# ============================================================

@app.get("/ask")
def ask_question(
    q: str
):

    try:

        # ----------------------------------------------------
        # Question
        # ----------------------------------------------------

        question = q.strip()


        if not question:

            return {

                "success": False,

                "message": (
                    "Question is required"
                )
            }


        # ----------------------------------------------------
        # API KEY CHECK
        # ----------------------------------------------------

        if not GROQ_API_KEY:

            return {

                "success": False,

                "message": (
                    "GROQ_API_KEY is missing. "
                    "Check backend/.env"
                )
            }


        if groq_client is None:

            return {

                "success": False,

                "message": (
                    "Groq client is not initialized"
                )
            }


        # ----------------------------------------------------
        # Document check
        # ----------------------------------------------------

        document_count = collection.count()


        if document_count == 0:

            return {

                "success": False,

                "message": (
                    "No PDF has been uploaded. "
                    "Please upload a PDF first."
                )
            }


        # ----------------------------------------------------
        # Search relevant chunks
        # ----------------------------------------------------

        results = collection.query(

            query_texts=[
                question
            ],

            n_results=min(
                5,
                document_count
            )
        )


        documents = results.get(
            "documents",
            [[]]
        )[0]


        metadatas = results.get(
            "metadatas",
            [[]]
        )[0]


        if not documents:

            return {

                "success": False,

                "message": (
                    "No relevant information found "
                    "in the uploaded documents."
                )
            }


        # ----------------------------------------------------
        # Build context
        # ----------------------------------------------------

        context_parts = []


        for index, document in enumerate(
            documents
        ):

            source = "Unknown"


            if index < len(metadatas):

                source = metadatas[index].get(
                    "source",
                    "Unknown"
                )


            context_parts.append(
                f"""
SOURCE: {source}

{document}
"""
            )


        context = "\n\n".join(
            context_parts
        )


        # ----------------------------------------------------
        # AI prompt
        # ----------------------------------------------------

        prompt = f"""
You are DevRAG, an AI document assistant.

Answer the user's question using ONLY
the information available in the document context.

Do not invent information.

If the answer is not available in the
document, say:

"The information is not available
in the uploaded document."

Keep the answer clear and useful.

DOCUMENT CONTEXT:
=================
{context}
=================

USER QUESTION:
{question}

ANSWER:
"""


        # ----------------------------------------------------
        # Groq API call
        # ----------------------------------------------------

        try:

            completion = (
                groq_client
                .chat
                .completions
                .create(

                    model="openai/gpt-oss-20b",

                    messages=[

                        {
                            "role": "system",

                            "content": (
                                "You are DevRAG, "
                                "a helpful document "
                                "question-answering "
                                "assistant."
                            )
                        },

                        {
                            "role": "user",

                            "content": prompt
                        }

                    ],

                    temperature=0.2,

                    max_tokens=500
                )
            )


        except Exception as groq_error:

            print(
                "GROQ ERROR:",
                str(groq_error)
            )


            error_text = str(
                groq_error
            )


            if (
                "401" in error_text
                or "Invalid API Key" in error_text
                or "invalid_api_key" in error_text
            ):

                return {

                    "success": False,

                    "message": (
                        "Groq API key is invalid. "
                        "Please create a new Groq API key "
                        "and update backend/.env."
                    )
                }


            return {

                "success": False,

                "message": (
                    f"Groq API error: {error_text}"
                )
            }


        # ----------------------------------------------------
        # Get answer
        # ----------------------------------------------------

        answer = (
            completion
            .choices[0]
            .message
            .content
        )


        # ----------------------------------------------------
        # Sources
        # ----------------------------------------------------

        sources = []


        for metadata in metadatas:

            source = metadata.get(
                "source",
                "Unknown"
            )


            if source not in sources:

                sources.append(
                    source
                )


        # ----------------------------------------------------
        # Response
        # ----------------------------------------------------

        return {

            "success": True,

            "question": question,

            "answer": answer,

            "sources": sources
        }


    except Exception as e:

        print(
            "ASK ERROR:",
            str(e)
        )

        return {

            "success": False,

            "message": (
                f"AI generation failed: {str(e)}"
            )
        }


# ============================================================
# 15. RUN SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        app,

        host="127.0.0.1",

        port=8000,

        reload=True
    )