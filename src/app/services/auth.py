from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from fastapi import HTTPException
from src.app.config import get_settings
from src.app.services.database import DatabaseService
import json
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

class GoogleAuth:
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/documents',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/drive.readonly'
    ]

    def __init__(self, client_id: str = None, client_secret: str = None, redirect_uri: str = None, credentials_file: str = None):
        """
        Initialize GoogleAuth with either explicit credentials or a credentials file.
        
        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            redirect_uri: OAuth redirect URI
            credentials_file: Path to credentials.json file
        """
        if credentials_file and os.path.exists(credentials_file):
            credentials = self._load_credentials_from_file(credentials_file)
            self.client_id = credentials.get('client_id')
            self.client_secret = credentials.get('client_secret')
            self.redirect_uri = credentials.get('redirect_uri')
            print(f"🔍 DEBUG: GoogleAuth initialized from credentials file {credentials_file}")
        else:
            self.client_id = client_id
            self.client_secret = client_secret
            self.redirect_uri = redirect_uri
            print(f"🔍 DEBUG: GoogleAuth initialized with client_id={client_id}")  # ✅ Debug statement
            
        if not self.client_id or not self.client_secret:
            raise ValueError("Client ID and Client Secret must be provided either directly or via credentials file")

    def _load_credentials_from_file(self, file_path: str) -> dict:
        """Load OAuth credentials from a JSON file."""
        try:
            with open(file_path, 'r') as file:
                credentials = json.load(file)
            
            # Check for required fields
            if 'web' in credentials:
                # Standard Google OAuth credentials.json format
                web_config = credentials['web']
                return {
                    'client_id': web_config.get('client_id'),
                    'client_secret': web_config.get('client_secret'),
                    'redirect_uri': web_config.get('redirect_uris', [''])[0]
                }
            elif all(key in credentials for key in ['client_id', 'client_secret']):
                # Simple format with direct keys
                return credentials
            else:
                raise ValueError("Invalid credentials format in file")
                
        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Failed to parse credentials file: {str(e)}")
            raise ValueError(f"Invalid JSON in credentials file: {str(e)}")
        except Exception as e:
            print(f"❌ ERROR: Failed to load credentials file: {str(e)}")
            raise ValueError(f"Failed to load credentials: {str(e)}")

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

    def is_token_expired(self, token_info: dict) -> bool:
        """Check if a token is expired or will expire soon (within 5 minutes)."""
        try:
            # Create credentials object
            credentials = Credentials(
                token=token_info['token'],
                refresh_token=token_info.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.SCOPES
            )
            
            # If no expiry set, consider it expired
            if not credentials.expiry:
                return True
                
            # Check if token is expired or will expire in next 5 minutes
            return credentials.expired or (
                credentials.expiry - datetime.utcnow() < timedelta(minutes=5)
            )
        except Exception as e:
            print(f"❌ ERROR checking token expiration: {str(e)}")
            return True

    def refresh_token(self, token_info: dict, db: Session = None) -> dict:
        """Refresh the access token and save to database if provided."""
        try:
            if not token_info.get('refresh_token'):
                raise HTTPException(
                    status_code=401,
                    detail="No refresh token available. Please re-authenticate."
                )

            credentials = Credentials(
                token=token_info['token'],
                refresh_token=token_info['refresh_token'],
                token_uri='https://oauth2.googleapis.com/token',
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.SCOPES
            )

            # Refresh the token
            request = Request()
            credentials.refresh(request)

            # Prepare the new token info
            new_token_info = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token or token_info['refresh_token'],
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }

            # Save to database if session provided
            if db:
                DatabaseService.save_tokens(
                    db,
                    access_token=new_token_info['token'],
                    refresh_token=new_token_info['refresh_token'],
                    expiry=credentials.expiry
                )
                print("✅ Refreshed token saved to database")

            return new_token_info

        except RefreshError as e:
            print(f"❌ Token refresh failed: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail="Token refresh failed. Please re-authenticate."
            )
        except Exception as e:
            print(f"❌ Unexpected error during token refresh: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Token refresh failed: {str(e)}"
            )

    async def validate_and_refresh_token(self, token_info: dict, db: Session) -> dict:
        """Validate a token and refresh if necessary."""
        try:
            if self.is_token_expired(token_info):
                print("🔄 Token expired, attempting refresh...")
                return self.refresh_token(token_info, db)
            return token_info
        except Exception as e:
            print(f"❌ Token validation failed: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail=f"Token validation failed: {str(e)}"
            )