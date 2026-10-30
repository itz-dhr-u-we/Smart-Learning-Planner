
import os
import datetime as datetime_lib

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, Column, Integer, Text, String,
    Float, Boolean, ForeignKey
)
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
if DB_URL and DB_URL.startswith("postgresql://"):
    DB_URL = DB_URL.replace(
        "postgresql://",
        "postgresql+psycopg2://",
        1
    )
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    try:
        DB_URL = st.secrets["DATABASE_URL"]
    except Exception:
        DB_URL = None

if not DB_URL:
    raise ValueError("DATABASE_URL not found. Check Streamlit Secrets.")

# Supabase PostgreSQL connection
engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()



# Existing database models

class user(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    institute = Column(String)
    global_exam_start = Column(String, nullable=True)


class subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    category = Column(String)
    credits = Column(Integer)

    topics = relationship(
        "topic", back_populates="subject",
        cascade="all, delete-orphan"
    )
    resources = relationship(
        "Resource", back_populates="subject",
        cascade="all, delete-orphan"
    )
    study_logs = relationship(
        "study_log", back_populates="subject",
        cascade="all, delete-orphan"
    )


class usersubject(Base):
    __tablename__ = "user_subjects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    exam_date = Column(String, nullable=True)


class topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    name = Column(String, nullable=False)
    confidence_score = Column(Integer, default=1)

    subject = relationship("subject", back_populates="topics")
    resources = relationship(
        "Resource", back_populates="topic",
        cascade="all, delete-orphan"
    )


class study_log(Base):
    __tablename__ = "study_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    duration_minutes = Column(Integer, nullable=True, default=25)
    notes = Column(Text, nullable=True)

    created_at = Column(
        String,
        nullable=False,
        default=lambda: datetime_lib.datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )
    )

    ai_chat_history = Column(String, nullable=True)

    subject = relationship("subject", back_populates="study_logs")


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    title = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    content_path_or_link = Column(String, nullable=True)
    confidence_score = Column(Integer, default=1)

    created_at = Column(
        String,
        nullable=False,
        default=lambda: datetime_lib.datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )
    )

    subject = relationship("subject", back_populates="resources")
    topic = relationship("topic", back_populates="resources")
    playlist_videos = relationship(
        "PlaylistVideo", back_populates="resource",
        cascade="all, delete-orphan"
    )


class PlaylistVideo(Base):
    __tablename__ = "playlist_videos"

    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)
    video_title = Column(String, nullable=False)
    video_url = Column(String, nullable=True)
    confidence_score = Column(Integer, default=1)
    is_completed = Column(Boolean, default=False)

    resource = relationship("Resource", back_populates="playlist_videos")


# New AI Tutor models

class TutorConversation(Base):
    __tablename__ = "tutor_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    study_log_id = Column(
        Integer, ForeignKey("study_logs.id"), nullable=True
    )

    title = Column(String, default="New Conversation")
    learning_mode = Column(String, default="Doubt Solving")

    created_at = Column(
        String,
        default=lambda: datetime_lib.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )
    updated_at = Column(
        String,
        default=lambda: datetime_lib.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    messages = relationship(
        "TutorMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="TutorMessage.id"
    )


class TutorMessage(Base):
    __tablename__ = "tutor_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("tutor_conversations.id"),
        nullable=False
    )

    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)

    created_at = Column(
        String,
        default=lambda: datetime_lib.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    conversation = relationship(
        "TutorConversation",
        back_populates="messages"
    )


def init_db():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
