from sqlalchemy.orm import Session
from app.models.database_models import Token
from datetime import datetime, timedelta

class TokenStore:
    @staticmethod
    def save_token(db: Session, access_token: str, refresh_token: str = None, expiry: datetime = None):
        """Save a token to the database"""
        if not expiry:
            expiry = datetime.utcnow() + timedelta(hours=1)  # Default expiry
            
        token = Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expiry=expiry
        )
        db.add(token)
        db.commit()
        db.refresh(token)
        return token
        
    @staticmethod
    def get_latest_token(db: Session):
        """Get the most recent token"""
        return db.query(Token).order_by(Token.created_at.desc()).first() 