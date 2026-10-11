import json
import math
from pathlib import Path
from dotenv import load_dotenv
from typing import List
from uuid import uuid4

from db import engine
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import Column, MetaData, String, Table, Text, insert, select

from pypdf import PdfReader
import docx2txt


load_dotenv()

Path("uploads").mkdir(exist_ok=True)

embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")

metadata = MetaData()
rag_documents = Table(
    "rag_documents",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("thread_id", String(255), nullable=False, index=True),
    Column("content", Text, nullable=False),
    Column("source", String(255), nullable=False),
    Column("embedding", Text, nullable=False),
)
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
    if suffix in [ ".txt", ".md"]:
        return file_path.read_text(encoding="utf-8", errors = "ignore")

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
    
    vectors = embeddings.embed_documents([document.page_content for document in documents])
    rows = [
        {
            "id": str(uuid4()),
            "thread_id": thread_id,
            "content": document.page_content,
            "source": document.metadata["source"],
            "embedding": json.dumps(vector),
        }
        for document, vector in zip(documents, vectors)
    ]
    with engine.begin() as connection:
        connection.execute(insert(rag_documents), rows)

    return{ "filename" : Path(file_path).name, "num_chunks": len(chunks)}


def _cosine_similarity(first: List[float], second: List[float]) -> float:
    numerator = sum(left * right for left, right in zip(first, second))
    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))
    if not first_norm or not second_norm:
        return 0.0
    return numerator / (first_norm * second_norm)


def retrieve_documents(query: str, thread_id: str, k: int = 5):
    """
    Retrieve documents from the vector store based on a query and thread_id.
    """
    query_vector = embeddings.embed_query(query)
    with engine.connect() as connection:
        rows = connection.execute(
            select(rag_documents.c.content, rag_documents.c.source, rag_documents.c.embedding)
            .where(rag_documents.c.thread_id == thread_id)
        ).mappings().all()

    ranked_rows = sorted(
        rows,
        key=lambda row: _cosine_similarity(query_vector, json.loads(row["embedding"])),
        reverse=True,
    )[:k]
    if not ranked_rows:
        return "No relevant documents found."
    return [
        {
            "chunk_index": index,
            "content": row["content"],
            "metadata": {"thread_id": thread_id, "source": row["source"]},
        }
        for index, row in enumerate(ranked_rows, start=1)
    ]