from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, JSON, Float,Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cv_id = Column(Integer, ForeignKey("cvs.id"), nullable=False)
    job_description_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False)

    type = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)

    total_questions = Column(Integer, nullable=False)
    current_question_index = Column(Integer, default=0)

    is_finished = Column(Boolean, default=False)

    result_json = Column(JSON, nullable=True) 
    final_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    cv_summary = Column(Text, nullable=True)

    # 🔗 Relationships
    user = relationship("User", back_populates="interviews")
    cv = relationship("CV")
    job_description = relationship("JobDescription")
    messages = relationship("InterviewMessage", back_populates="interview", cascade="all, delete")
