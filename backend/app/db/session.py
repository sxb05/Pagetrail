from datetime import datetime

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.models import ChatMessage, Conversation, LongTermMemory


def _looks_like_database_url(value: str) -> bool:
    stripped = value.strip()
    if stripped.startswith(("f\"", "f'", "F\"", "F'")):
        return False
    return stripped.startswith(("postgresql://", "postgres://", "postgresql+psycopg://"))


def _database_url() -> URL:
    # Build from discrete fields so passwords with @, &, :, / stay unparsed as host.
    if settings.DATABASE_URL and _looks_like_database_url(settings.DATABASE_URL):
        parsed_url = make_url(settings.DATABASE_URL.strip())
        return parsed_url.set(drivername="postgresql+psycopg")
    return URL.create(
        drivername="postgresql+psycopg",
        username=settings.DATABASE_USERNAME,
        password=settings.DATABASE_PASSWORD,
        host=settings.DATABASE_HOST,
        port=int(settings.DATABASE_PORT),
        database=settings.DATABASE_NAME,
    )



database_url = _database_url()


def _database_admin_url() -> URL:
    if not settings.DATABASE_ADMIN_URL:
        # Temporary compatibility fallback. This does not separate roles
        # until DATABASE_ADMIN_URL is configured.
        return database_url

    admin_value = settings.DATABASE_ADMIN_URL.strip()
    if not _looks_like_database_url(admin_value):
        raise ValueError(
            "DATABASE_ADMIN_URL must be a valid PostgreSQL URL."
        )

    return make_url(admin_value).set(drivername="postgresql+psycopg")


def _connect_args_for(url: URL) -> dict:
    if url.host and url.host != "localhost":
        return {"sslmode": "require"}
    return {}


admin_database_url = _database_admin_url()

# Ordinary application queries use this engine.
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args=_connect_args_for(database_url),
)

# Schema initialization and migrations use this engine.
admin_engine = create_engine(
    admin_database_url,
    pool_pre_ping=True,
    connect_args=_connect_args_for(admin_database_url),
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    rls_tables = (
        "users",
        "conversations",
        "chat_messages",
        "long_term_memory",
        "rag_documents",
    )
    migrations = {
        "conversations": "user_id",
        "chat_messages": "user_id",
        "long_term_memory": "user_id",
    }
    with admin_engine.begin() as connection:
        # Keep schema initialization and inspection on one connection and give
        # remote PostgreSQL metadata queries enough time to complete.
        connection.exec_driver_sql("SET LOCAL statement_timeout = '30s'")
        Base.metadata.create_all(bind=connection)
        inspector = inspect(connection)
        for table_name in rls_tables:
            connection.execute(
                text(f"ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY")
            )
        for table_name, column_name in migrations.items():
            existing_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            if column_name not in existing_columns:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} ADD COLUMN {column_name} "
                        "INTEGER REFERENCES users(id)"
                    )
                )


def create_update_convo(
    thread_id: str, user_id: int, first_message: str, name: str = "New Conversation"
) -> bool:
    session = SessionLocal()
    try:
        conversation = session.query(Conversation).filter_by(thread_id=thread_id).first()
        if conversation:
            if conversation.user_id != user_id:
                return False
            conversation.name = name
            conversation.updated_at = datetime.utcnow().isoformat()
        else:
            conversation = Conversation(thread_id=thread_id, user_id=user_id, name=name)
            session.add(conversation)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def conversation_belongs_to_user(thread_id: str, user_id: int) -> bool:
    session = SessionLocal()
    try:
        return (
            session.query(Conversation)
            .filter_by(thread_id=thread_id, user_id=user_id)
            .first()
            is not None
        )
    finally:
        session.close()


def list_conversations(user_id: int):
    session = SessionLocal()
    try:
        conversations = (
            session.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )
        return conversations
    except Exception as e:
        raise e
    finally:
        session.close()


def save_chat_message(thread_id: str, user_id: int, role: str, content: str) -> bool:
    session = SessionLocal()
    try:
        conversation = (
            session.query(Conversation)
            .filter_by(thread_id=thread_id, user_id=user_id)
            .first()
        )
        if conversation is None:
            return False
        message = ChatMessage(
            thread_id=thread_id, user_id=user_id, role=role, content=content
        )
        session.add(message)
        conversation.updated_at = datetime.utcnow().isoformat()
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def save_memory(thread_id: str, user_id: int, content: str):
    session = SessionLocal()
    try:
        conversation = (
            session.query(Conversation)
            .filter(
                Conversation.thread_id == thread_id,
                Conversation.user_id == user_id,
            )
            .first()
        )

        if conversation is None:
            raise ValueError("Conversation not found or access denied.")

        memory = LongTermMemory(
            thread_id=thread_id,
            user_id=user_id,
            content=content,
        )

        session.add(memory)
        conversation.updated_at = datetime.utcnow().isoformat()
        session.commit()

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def search_memory(thread_id: str, user_id: int, query: str):
    session = SessionLocal()
    try:
        memories = (
            session.query(LongTermMemory)
            .filter(
                LongTermMemory.thread_id == thread_id,
                LongTermMemory.user_id == user_id,
                LongTermMemory.content.contains(query),
            )
            .all()
        )
        return memories

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_chat_history(thread_id: str, user_id: int):
    session = SessionLocal()
    try:
        messages = (
            session.query(ChatMessage)
            .filter(
                ChatMessage.thread_id == thread_id,
                ChatMessage.user_id == user_id,
            )
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        return messages
    except Exception as e:
        raise e
    finally:
        session.close()


def delete_conversation(thread_id: str, user_id: int) -> bool:
    session = SessionLocal()
    try:
        conversation = (
            session.query(Conversation)
            .filter_by(thread_id=thread_id, user_id=user_id)
            .first()
        )
        if conversation is None:
            return False
        session.delete(conversation)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    print("Database connection OK")
