from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    parent_id = Column(Integer, ForeignKey("topics.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    parent = relationship("Topic", remote_side=[id], backref="children")
    bookmarks = relationship(
        "Bookmark", back_populates="topic", cascade="all, delete-orphan"
    )


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True)
    title = Column(String(512), nullable=False)
    url = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    topic_id = Column(Integer, ForeignKey("topics.id"), index=True, nullable=False)
    topic = relationship("Topic", back_populates="bookmarks")


