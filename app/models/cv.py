from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class CV(Base):
    __tablename__ = "cvs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_name = Column(String)
    file_path = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 🔗 Relationships
    user = relationship("User", back_populates="cvs")
    interviews = relationship("Interview", back_populates="cv", cascade="all, delete")
