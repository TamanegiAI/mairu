from sqlalchemy.orm import Session
from app.models import database_models
from datetime import datetime
from typing import Optional, Dict

class DatabaseService:
    @staticmethod
    def save_tokens(db: Session, access_token: str, refresh_token: str):
        token = database_models.Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expiry=datetime.utcnow()  # You should calculate proper expiry
        )
        db.add(token)
        db.commit()
        db.refresh(token)
        return token

    @staticmethod
    def get_latest_tokens(db: Session):
        return db.query(database_models.Token).order_by(
            database_models.Token.created_at.desc()
        ).first()

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