import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import session as db_session
from app.db.base import Base
from app.db.models import (
    ChatMessage,
    Conversation,
    LongTermMemory,
    User,
)


@pytest.fixture
def isolated_db(monkeypatch):
    """Create an isolated database with two unrelated users."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    TestSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    # Make the application's database functions use the test database.
    monkeypatch.setattr(db_session, "SessionLocal", TestSessionLocal)

    with TestSessionLocal() as db:
        user_a = User(username="user_a", password_hash="test-hash-a")
        user_b = User(username="user_b", password_hash="test-hash-b")
        db.add_all([user_a, user_b])
        db.flush()

        conversation_a = Conversation(
            thread_id="thread-a",
            user_id=user_a.id,
            name="User A conversation",
        )
        conversation_b = Conversation(
            thread_id="thread-b",
            user_id=user_b.id,
            name="User B conversation",
        )
        db.add_all([conversation_a, conversation_b])
        db.flush()

        db.add_all(
            [
                ChatMessage(
                    thread_id="thread-a",
                    user_id=user_a.id,
                    role="user",
                    content="A private message",
                ),
                ChatMessage(
                    thread_id="thread-b",
                    user_id=user_b.id,
                    role="user",
                    content="B private message",
                ),
                LongTermMemory(
                    thread_id="thread-a",
                    user_id=user_a.id,
                    content="A private memory",
                ),
                LongTermMemory(
                    thread_id="thread-b",
                    user_id=user_b.id,
                    content="B private memory",
                ),
            ]
        )
        db.commit()

        result = {
            "user_a_id": user_a.id,
            "user_b_id": user_b.id,
        }

    yield result

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_user_cannot_access_other_users_conversation(isolated_db):
    user_a_id = isolated_db["user_a_id"]

    assert db_session.conversation_belongs_to_user("thread-b", user_a_id) is False

    assert db_session.conversation_belongs_to_user("thread-a", user_a_id) is True


def test_user_only_lists_own_conversations(isolated_db):
    user_a_id = isolated_db["user_a_id"]

    conversations = db_session.list_conversations(user_a_id)

    assert {c.thread_id for c in conversations} == {"thread-a"}


def test_user_cannot_read_other_users_messages(isolated_db):
    user_a_id = isolated_db["user_a_id"]

    own_messages = db_session.get_chat_history("thread-a", user_a_id)
    other_messages = db_session.get_chat_history("thread-b", user_a_id)

    assert [m.content for m in own_messages] == ["A private message"]
    assert other_messages == []


def test_user_cannot_search_other_users_memories(isolated_db):
    user_a_id = isolated_db["user_a_id"]

    own_memories = db_session.search_memory("thread-a", user_a_id, "private memory")
    other_memories = db_session.search_memory("thread-b", user_a_id, "private memory")

    assert [m.content for m in own_memories] == ["A private memory"]
    assert other_memories == []


def test_user_cannot_save_memory_to_other_users_conversation(isolated_db):
    user_a_id = isolated_db["user_a_id"]
    user_b_id = isolated_db["user_b_id"]

    with pytest.raises(ValueError, match="access denied"):
        db_session.save_memory("thread-b", user_a_id, "Unauthorized memory")

    assert db_session.search_memory("thread-b", user_b_id, "Unauthorized memory") == []


def test_user_can_save_and_search_own_memory(isolated_db):
    user_a_id = isolated_db["user_a_id"]

    db_session.save_memory("thread-a", user_a_id, "I prefer Python")

    memories = db_session.search_memory("thread-a", user_a_id, "prefer Python")

    assert [m.content for m in memories] == ["I prefer Python"]


def test_document_retrieval_only_returns_documents_for_owner(monkeypatch):
    from types import SimpleNamespace

    from sqlalchemy import create_engine, insert, literal
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.db.base import Base
    from app.db.models import User, Conversation
    from app.services import rag

    # A separate, in-memory test database: never connects to Supabase.
    test_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    try:
        Base.metadata.create_all(bind=test_engine)
        rag.metadata.create_all(bind=test_engine)
        monkeypatch.setattr(rag, "engine", test_engine)
        TestSessionLocal = sessionmaker(
            bind=test_engine,
            autoflush=False,
            autocommit=False,
        )

        with TestSessionLocal() as db:
            user_a = User(username="doc_user_a", password_hash="test-hash-a")
            user_b = User(username="doc_user_b", password_hash="test-hash-b")
            db.add_all([user_a, user_b])
            db.flush()

            user_a_id = user_a.id
            user_b_id = user_b.id

            db.add_all(
                [
                    Conversation(
                        thread_id="doc-thread-a",
                        user_id=user_a_id,
                        name="A's conversation",
                    ),
                    Conversation(
                        thread_id="doc-thread-b",
                        user_id=user_b_id,
                        name="B's conversation",
                    ),
                ]
            )
            db.commit()

        # Give each user a separate document in the vector-store table.
        vector = [0.0] * rag.EMBEDDING_DIM

        with test_engine.begin() as connection:
            connection.execute(
                insert(rag.rag_documents),
                [
                    {
                        "id": "doc-a",
                        "thread_id": "doc-thread-a",
                        "content": "A private document",
                        "source": "a.txt",
                        "embedding": "[]",
                        "embedding_vector": vector,
                    },
                    {
                        "id": "doc-b",
                        "thread_id": "doc-thread-b",
                        "content": "B private document",
                        "source": "b.txt",
                        "embedding": "[]",
                        "embedding_vector": vector,
                    },
                ],
            )

        # Route the retrieval function to the isolated database.
        monkeypatch.setattr(
            rag,
            "_get_embeddings",
            lambda: SimpleNamespace(
                embed_query=lambda query: vector,
                embed_documents=lambda texts: [vector for _ in texts],
            ),
        )

        # SQLite doesn't implement pgvector's cosine-distance operator.
        # Replace only that expression; execute the real ownership-filtered
        # SQL query against SQLite.
        comparator_type = type(rag.rag_documents.c.embedding_vector.comparator)
        monkeypatch.setattr(
            comparator_type,
            "cosine_distance",
            lambda self, other: literal(0.0),
        )

        # User A can retrieve A's document.
        own_results = rag.retrieve_documents(
            "private document",
            "doc-thread-a",
            user_a_id,
            k=5,
        )

        assert isinstance(own_results, list)
        assert [item["content"] for item in own_results] == ["A private document"]

        # Even when given B's conversation ID, User A cannot retrieve B's data.
        other_results = rag.retrieve_documents(
            "private document",
            "doc-thread-b",
            user_a_id,
            k=5,
        )

        assert other_results == "No relevant documents found."

        # User B can still retrieve B's own document.
        user_b_results = rag.retrieve_documents(
            "private document",
            "doc-thread-b",
            user_b_id,
            k=5,
        )

        assert isinstance(user_b_results, list)
        assert [item["content"] for item in user_b_results] == ["B private document"]

    finally:
        rag.metadata.drop_all(bind=test_engine)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()

        
def test_checkpoint_ids_are_isolated_by_user():
    from app.api.routes.chat import build_checkpoint_thread_id

    conversation_id = "shared-test-conversation"

    user_a_checkpoint = build_checkpoint_thread_id(101, conversation_id)
    user_b_checkpoint = build_checkpoint_thread_id(202, conversation_id)

    # The same conversation ID must not produce a shared checkpoint.
    assert user_a_checkpoint != user_b_checkpoint

    # The same user and conversation must produce a stable checkpoint ID.
    assert user_a_checkpoint == build_checkpoint_thread_id(
        101, conversation_id
    )