from sqlalchemy import Column, Integer, String, Text, DateTime, func
from db.session import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    room = Column(String(50), index=True)
    username = Column(String(50))
    message = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())