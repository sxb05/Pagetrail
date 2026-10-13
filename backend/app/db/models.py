from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base, utcnow_iso


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(255), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(String(255), default=utcnow_iso)
    updated_at = Column(String(255), default=utcnow_iso, onupdate=utcnow_iso)
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")
    long_term_memories = relationship(
        "LongTermMemory",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, ForeignKey("conversations.thread_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(String(255), default=utcnow_iso)
    updated_at = Column(String(255), default=utcnow_iso, onupdate=utcnow_iso)

    conversation = relationship("Conversation", back_populates="messages")


class LongTermMemory(Base):
    __tablename__ = "long_term_memory"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, ForeignKey("conversations.thread_id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(String(255), default=utcnow_iso)
    updated_at = Column(String(255), default=utcnow_iso, onupdate=utcnow_iso)

    conversation = relationship("Conversation", back_populates="long_term_memories")
