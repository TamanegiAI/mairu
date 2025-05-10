from src.app.config import get_settings
from src.app.services.auth import GoogleAuth
import os

def get_google_auth() -> GoogleAuth:
    settings = get_settings()
    print(f"🔍 DEBUG: Creating new GoogleAuth instance")
    
    # Check for credentials file in environment
    credentials_file = os.environ.get('GOOGLE_CREDENTIALS_FILE')
    
    if credentials_file and os.path.exists(credentials_file):
        print(f"🔍 DEBUG: Using credentials from file: {credentials_file}")
        return GoogleAuth(credentials_file=credentials_file)
    
    # If no credentials file, ensure we have the required settings
    if not settings.google_client_id or not settings.google_client_secret:
        raise ValueError("Missing Google OAuth credentials. Please provide either a credentials.json file or set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.")
        
    # Use settings-based authentication
    print(f"🔍 DEBUG: Using client_id from settings")
    return GoogleAuth(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri
    )