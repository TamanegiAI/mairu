from sqlalchemy.orm import Session
from src.app.models import database_models
from datetime import datetime, timedelta
from typing import Optional, Dict
import os

class DatabaseService:
    # Configuration with environment variables and defaults
    TOKEN_HISTORY_DAYS = int(os.getenv('TOKEN_HISTORY_DAYS', '7'))
    KEEP_MIN_TOKENS = int(os.getenv('KEEP_MIN_TOKENS', '5'))

    @staticmethod
    def save_tokens(db: Session, access_token: str, refresh_token: str, expiry: datetime = None):
        """
        Save tokens using hybrid approach:
        - Always create a new token record
        - Clean up old tokens beyond retention period
        - Ensure minimum number of tokens are kept
        """
        try:
            # Create new token record
            token = database_models.Token(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expiry=expiry
            )
            db.add(token)
            db.flush()  # Flush to get the ID but don't commit yet

            # Calculate cleanup threshold date
            cleanup_threshold = datetime.utcnow() - timedelta(days=DatabaseService.TOKEN_HISTORY_DAYS)

            # Get all tokens ordered by creation date
            all_tokens = db.query(database_models.Token).order_by(
                database_models.Token.created_at.desc()
            ).all()

            # Keep track of tokens to delete
            tokens_to_delete = []
            for idx, old_token in enumerate(all_tokens):
                # Keep minimum number of tokens regardless of age
                if idx < DatabaseService.KEEP_MIN_TOKENS:
                    continue
                # Delete tokens beyond retention period
                if old_token.created_at < cleanup_threshold:
                    tokens_to_delete.append(old_token)

            # Delete old tokens
            for old_token in tokens_to_delete:
                db.delete(old_token)

            # Commit all changes
            db.commit()
            db.refresh(token)
            print(f"✅ Token saved and cleaned up old tokens. Deleted: {len(tokens_to_delete)}")
            return token

        except Exception as e:
            db.rollback()
            print(f"❌ Error saving tokens: {str(e)}")
            raise

    @staticmethod
    def get_latest_tokens(db: Session):
        """Get the most recent valid token."""
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