import json
import math
from pathlib import Path
from typing import List
from uuid import uuid4

import docx2txt
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy import Column, MetaData, String, Table, Text, insert, select
from pgvector.sqlalchemy import Vector
# from app.core.paths import UPLOAD_DIR
from app.db.session import engine

# UPLOAD_DIR.mkdir(exist_ok=True)

embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")


# Generate a sample embedding first
sample_vector = embeddings.embed_query("test text")

# Now check the dimension of that vector
print("Embedding dimension:", len(sample_vector))

print("Embedding type:", type(embeddings))
EMBEDDING_DIM = 3072

metadata = MetaData()
rag_documents = Table(
    "rag_documents",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("thread_id", String(255), nullable=False, index=True),
    Column("content", Text, nullable=False),
    Column("source", String(255), nullable=False),
    Column("embedding", Text, nullable=False),
    Column("embedding_vector", Vector(EMBEDDING_DIM), nullable=True),
)


def init_rag_db() -> None:
    metadata.create_all(bind=engine)


def read_pdf(file_path: str) -> str:
    """
    Read a PDF file and return its text content.
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        pdf_reader = PdfReader(file_path)
        text = ""
        for page in pdf_reader.pages:
            text += (page.extract_text() or "") + "\n"
        return text
    if suffix == ".docx":
        text = docx2txt.process(file_path)
        return text
    if suffix in [".txt", ".md"]:
        return file_path.read_text(encoding="utf-8", errors="ignore")

    raise ValueError(f"Unsupported file type: {suffix}, Please provide a PDF, DOCX, TXT, or MD file.")


def add_document_to_vector_store(file_path: str, thread_id: str):
    """
    Read a document, split it into chunks, and add it to the vector store.
    """
    text = read_pdf(file_path)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)
    documents: List[Document] = [
        Document(
            page_content=chunk,
            metadata={"thread_id": thread_id, "source": Path(file_path).name},
        )
        for chunk in chunks
    ]

    vectors = embeddings.embed_documents(
    [document.page_content for document in documents]
)

    rows = []

    for document, vector in zip(documents, vectors):
        if len(vector) != 3072:
            raise ValueError(
                f"Expected 3072 dimensions, received {len(vector)}"
            )

        rows.append(
            {
                "id": str(uuid4()),
                "thread_id": thread_id,
                "content": document.page_content,
                "source": document.metadata["source"],
                "embedding": json.dumps(vector),  # Keep existing JSON storage
                "embedding_vector": vector,       # New pgvector storage
            }
        )
    with engine.begin() as connection:
        connection.execute(insert(rag_documents), rows)

    return {"filename": Path(file_path).name, "num_chunks": len(chunks)}


def _cosine_similarity(first: List[float], second: List[float]) -> float:
    numerator = sum(left * right for left, right in zip(first, second))
    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))
    if not first_norm or not second_norm:
        return 0.0
    return numerator / (first_norm * second_norm)


def retrieve_documents(query: str, thread_id: str, k: int = 5):
    """
    Retrieve the top-k relevant document chunks using pgvector.
    """
    query_vector = embeddings.embed_query(query)

    if len(query_vector) != EMBEDDING_DIM:
        raise ValueError(
            f"Expected {EMBEDDING_DIM} dimensions, "
            f"received {len(query_vector)}"
        )

    distance = rag_documents.c.embedding_vector.cosine_distance(
        query_vector
    ).label("distance")

    statement = (
        select(
            rag_documents.c.content,
            rag_documents.c.source,
            distance,
        )
        .where(
            rag_documents.c.thread_id == thread_id,
            rag_documents.c.embedding_vector.is_not(None),
        )
        .order_by(distance)
        .limit(max(1, k))
    )

    with engine.connect() as connection:
        ranked_rows = connection.execute(
            statement
        ).mappings().all()

    if not ranked_rows:
        return "No relevant documents found."

    return [
        {
            "chunk_index": index,
            "content": row["content"],
            "metadata": {
                "thread_id": thread_id,
                "source": row["source"],
            },
        }
        for index, row in enumerate(ranked_rows, start=1)
    ]