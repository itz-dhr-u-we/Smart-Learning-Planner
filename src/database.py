import os
from sqlalchemy import create_engine, Column, Integer, Text, String, Float,Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker,relationship
import datetime as datetime_lib
#db setup
DB_URL = "sqlite:///./smart_learning_planner.db"
engine = create_engine(DB_URL,connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind = engine)

Base = declarative_base()

#db models

class user(Base):
    __tablename__ = "users"
    id = Column(Integer,primary_key=True,index=True)
    username = Column(String,unique=True,index=True)
    password_hash = Column(String)
    institute = Column(String)
    global_exam_start = Column(String,nullable=True)
    
class subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer,primary_key=True,index=True)
    name = Column(String,unique=True,index=True)
    category = Column(String) #Therory,Lab,Others
    credits = Column(Integer)
    topics = relationship("topic", back_populates="subject", cascade="all, delete-orphan")
    resources = relationship("Resource", back_populates="subject", cascade="all, delete-orphan")

class usersubject(Base):
    __tablename__ = "user_subjects"
    id = Column(Integer,primary_key=True,index=True)
    user_id  = Column(Integer,ForeignKey("users.id"))
    subject_id = Column(Integer,ForeignKey("subjects.id"))
    exam_date = Column(String,nullable=True) # YYYY-MM-DD format

class topic(Base):
    __tablename__ = "topics"
    id = Column(Integer,primary_key=True,index=True)
    subject_id = Column(Integer,ForeignKey("subjects.id"),nullable=False)
    name = Column(String,nullable=False)
    confidence_score = Column(Integer,default=1) # 1-10 scale
    subject = relationship("subject", back_populates="topics")
    resources = relationship("Resource", back_populates="topic", cascade="all, delete-orphan")

class study_log(Base):
    __tablename__ = "study_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    duration_minutes = Column(Integer, default=25)
    timestamp = Column(String, nullable=True) # Stored date/time string
    notes = Column(Text, nullable=True)

class Resource(Base):
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"),nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    title = Column(String,nullable=False)
    resource_type = Column(String,nullable=False) # "PDF", "Book", "YouTube"
    
    content_path_or_link = Column(String,nullable=True) # File path for PDF or URL for YT/Book
    confidence_score = Column(Integer,default=1)
    created_at = Column(String,nullable=False, default=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

    subject = relationship("subject",back_populates="resources")
    topic = relationship("topic",back_populates="resources")
    playlist_videos = relationship("PlaylistVideo", back_populates="resource", cascade="all, delete-orphan")

class PlaylistVideo(Base):
    __tablename__ = "playlist_videos"
    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id"),nullable=False)
    video_title = Column(String,nullable=False)
    video_url = Column(String, nullable=True)  # Individual link for the parsed playlist video
    confidence_score = Column(Integer, default=1)  # 1-10 scale for individual video tracking
    is_completed = Column(Boolean, default=False)  # Manually ticked by student

    resource = relationship("Resource", back_populates="playlist_videos")

def init_db():
    Base.metadata.create_all(bind = engine)

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")