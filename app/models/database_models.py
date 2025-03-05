from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from app.database import Base

class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    access_token = Column(String, index=True)
    refresh_token = Column(String)
    token_type = Column(String)
    expiry = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class ColumnMapping(Base):
    __tablename__ = "column_mappings"

    id = Column(Integer, primary_key=True, index=True)
    sheet_id = Column(String, index=True)
    template_id = Column(String)
    mappings = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())

class ScheduledEmail(Base):
    __tablename__ = "scheduled_emails"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True)
    to_email = Column(String)
    subject = Column(String)
    body = Column(String)
    cc = Column(String, nullable=True)
    document_id = Column(String, nullable=True)
    scheduled_time = Column(DateTime)
    status = Column(String)  # pending, sent, failed, cancelled
    created_at = Column(DateTime, server_default=func.now()) 