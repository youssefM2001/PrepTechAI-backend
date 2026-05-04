from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String,unique=True,nullable=False)
    password_hash = Column(String,nullable=False)
    createdAt = Column(DateTime,default=datetime.utcnow)

    cvs = relationship("CV", back_populates="user", cascade="all, delete")
    interviews = relationship("Interview", back_populates="user", cascade="all, delete")
    jobs = relationship("JobDescription", back_populates="user", cascade="all, delete")
