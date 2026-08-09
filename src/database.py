import os
from sqlalchemy import create_engine, Column, Integer, Text, String, Float,Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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

class usersubject(Base):
    __tablename__ = "user_subjects"
    id = Column(Integer,primary_key=True,index=True)
    user_id  = Column(Integer,ForeignKey("users.id"))
    subject_id = Column(Integer,ForeignKey("subjects.id"))
    exam_date = Column(String,nullable=True) # YYYY-MM-DD format

class topic(Base):
    __tablename__ = "topics"
    id = Column(Integer,primary_key=True,index=True)
    subject_id = Column(Integer,ForeignKey("subjects.id"))
    name = Column(String)
    is_covered = Column(Boolean,default = False)
    confidence_score = Column(Float,default=0.0) # 1-10 scale
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
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    resource_type = Column(String) # "PDF", "Book", "YouTube"
    title = Column(String)
    content_path_or_link = Column(String) # File path for PDF or URL for YT/Book

class PlaylistVideo(Base):
    __tablename__ = "playlist_videos"
    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id"))
    video_title = Column(String)
    is_completed = Column(Boolean, default=False) # Manually ticked by student

def init_db():
    Base.metadata.create_all(bind = engine)

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")