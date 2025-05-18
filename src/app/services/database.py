from sqlalchemy.orm import Session
from src.app.models import database_models
from datetime import datetime, timedelta
from typing import Optional, Dict
import os

class DatabaseService:
    # Token storage functionality has been removed - using only file-based token storage via TokenStore

    @staticmethod
    def save_column_mapping(
        db: Session,
        sheet_id: str,
        template_id: str,
        mappings: Dict
    ):
        mapping = database_models.ColumnMapping(
            sheet_id=sheet_id,
            template_id=template_id,
            mappings=mappings
        )
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        return mapping

    @staticmethod
    def get_column_mapping(db: Session, sheet_id: str):
        return db.query(database_models.ColumnMapping).filter(
            database_models.ColumnMapping.sheet_id == sheet_id
        ).first()

    @staticmethod
    def save_scheduled_email(
        db: Session,
        job_id: str,
        to_email: str,
        subject: str,
        body: str,
        scheduled_time: datetime,
        cc: Optional[str] = None,
        document_id: Optional[str] = None
    ):
        scheduled_email = database_models.ScheduledEmail(
            job_id=job_id,
            to_email=to_email,
            subject=subject,
            body=body,
            cc=cc,
            document_id=document_id,
            scheduled_time=scheduled_time,
            status="pending"
        )
        db.add(scheduled_email)
        db.commit()
        db.refresh(scheduled_email)
        return scheduled_email

    @staticmethod
    def update_scheduled_email_status(
        db: Session,
        job_id: str,
        status: str
    ):
        scheduled_email = db.query(database_models.ScheduledEmail).filter(
            database_models.ScheduledEmail.job_id == job_id
        ).first()
        if scheduled_email:
            scheduled_email.status = status
            db.commit()
            db.refresh(scheduled_email)
        return scheduled_email