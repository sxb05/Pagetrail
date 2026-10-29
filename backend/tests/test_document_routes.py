import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import chat as chat_route
from app.db import session as db_session
from app.db.base import Base
from app.db.models import Conversation, User
from app.schemas.auth import UserResponse
from app.services import rag


@pytest.fixture
def doc_test_env(monkeypatch):
    test_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=test_engine)
    rag.metadata.create_all(bind=test_engine)

    monkeypatch.setattr(db_session, "engine", test_engine)
    monkeypatch.setattr(chat_route, "engine", test_engine)
    monkeypatch.setattr(rag, "engine", test_engine)

    TestSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )
    monkeypatch.setattr(db_session, "SessionLocal", TestSessionLocal)

    with TestSessionLocal() as db:
        user_a = User(username="user_alice", password_hash="hash-alice")
        user_b = User(username="user_bob", password_hash="hash-bob")
        db.add_all([user_a, user_b])
        db.flush()

        conv_a = Conversation(
            thread_id="thread-alice",
            user_id=user_a.id,
            name="Alice Convo",
        )
        conv_b = Conversation(
            thread_id="thread-bob",
            user_id=user_b.id,
            name="Bob Convo",
        )
        db.add_all([conv_a, conv_b])
        db.commit()

        # Insert documents for both users
        with test_engine.begin() as conn:
            conn.execute(
                insert(rag.rag_documents),
                [
                    {
                        "id": "doc-a1",
                        "thread_id": "thread-alice",
                        "content": "Alice doc content 1",
                        "source": "alice_notes.pdf",
                        "embedding": "[]",
                    },
                    {
                        "id": "doc-a2",
                        "thread_id": "thread-alice",
                        "content": "Alice doc content 2",
                        "source": "alice_notes.pdf",
                        "embedding": "[]",
                    },
                    {
                        "id": "doc-a3",
                        "thread_id": "thread-alice",
                        "content": "Alice summary content",
                        "source": "summary.txt",
                        "embedding": "[]",
                    },
                    {
                        "id": "doc-b1",
                        "thread_id": "thread-bob",
                        "content": "Bob secret content",
                        "source": "bob_secret.docx",
                        "embedding": "[]",
                    },
                ],
            )

        yield {
            "user_a": UserResponse(id=user_a.id, username=user_a.username),
            "user_b": UserResponse(id=user_b.id, username=user_b.username),
        }

    rag.metadata.drop_all(bind=test_engine)
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_list_files_for_owner(doc_test_env):
    user_a = doc_test_env["user_a"]
    files = chat_route.list_files("thread-alice", user_a)
    filenames = {f["filename"] for f in files}
    assert filenames == {"alice_notes.pdf", "summary.txt"}

    # alice_notes.pdf has 2 chunks
    notes_file = next(f for f in files if f["filename"] == "alice_notes.pdf")
    assert notes_file["num_chunks"] == 2


def test_user_cannot_list_other_users_files(doc_test_env):
    user_a = doc_test_env["user_a"]
    with pytest.raises(HTTPException) as exc_info:
        chat_route.list_files("thread-bob", user_a)
    assert exc_info.value.status_code == 404


def test_delete_file_for_owner(doc_test_env):
    user_a = doc_test_env["user_a"]
    result = chat_route.delete_file("thread-alice", "summary.txt", user_a)
    assert result == {"deleted": True}

    remaining_files = chat_route.list_files("thread-alice", user_a)
    assert [f["filename"] for f in remaining_files] == ["alice_notes.pdf"]


def test_user_cannot_delete_other_users_file(doc_test_env):
    user_a = doc_test_env["user_a"]
    with pytest.raises(HTTPException) as exc_info:
        chat_route.delete_file("thread-bob", "bob_secret.docx", user_a)
    assert exc_info.value.status_code == 404

    # Bob's file still intact
    user_b = doc_test_env["user_b"]
    bob_files = chat_route.list_files("thread-bob", user_b)
    assert [f["filename"] for f in bob_files] == ["bob_secret.docx"]

