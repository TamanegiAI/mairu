from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from fastapi import HTTPException
from app.config import get_settings
import json

class GoogleAuth:
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/documents',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/drive.readonly'
    ]

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        print(f"🔍 DEBUG: GoogleAuth initialized with client_id={client_id}")  # ✅ Debug statement
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self) -> str:
        print(f"🔍 DEBUG: Creating auth URL with client_id={self.client_id}")
        
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [self.redirect_uri],
                "javascript_origins": ["http://localhost:8000"]
            }
        }
        
        print(f"🔍 DEBUG: Client config: {client_config}")
        
        try:
            flow = Flow.from_client_config(
                client_config,
                scopes=self.SCOPES,
                redirect_uri=self.redirect_uri
            )
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'  # Force consent screen to ensure refresh token
            )
            
            print(f"🔍 DEBUG: Generated auth URL: {authorization_url}")
            return authorization_url
        except Exception as e:
            print(f"❌ ERROR: Failed to create authorization URL: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create authorization URL: {str(e)}"
            )

    def get_tokens(self, code: str) -> dict:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            scopes=self.SCOPES
        )
        flow.redirect_uri = self.redirect_uri
        flow.fetch_token(code=code)
        return {
            'token': flow.credentials.token,
            'refresh_token': flow.credentials.refresh_token,
            'token_uri': flow.credentials.token_uri,
            'client_id': flow.credentials.client_id,
            'client_secret': flow.credentials.client_secret,
            'scopes': flow.credentials.scopes
        }

    def refresh_token(self, token_info: dict) -> dict:
        try:
            credentials = Credentials(
                token=token_info['token'],
                refresh_token=token_info['refresh_token'],
                token_uri=token_info['token_uri'],
                client_id=token_info['client_id'],
                client_secret=token_info['client_secret'],
                scopes=token_info['scopes']
            )
            
            if not credentials.refresh_token:
                raise HTTPException(
                    status_code=401,
                    detail="No refresh token available. Please log in again."
                )
            
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                return {
                    'token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'token_uri': credentials.token_uri,
                    'client_id': credentials.client_id,
                    'client_secret': credentials.client_secret,
                    'scopes': credentials.scopes
                }
            return token_info
        except RefreshError:
            raise HTTPException(
                status_code=401,
                detail="Token refresh failed. Please re-authenticate."
            ) 