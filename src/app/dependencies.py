from src.app.config import get_settings
from src.app.services.auth import GoogleAuth
import os

def get_google_auth() -> GoogleAuth:
    settings = get_settings()
    print(f"🔍 DEBUG: Creating new GoogleAuth instance")
    
    # First try to use the credentials file in the app directory 
    app_creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
    
    # Check for overridden credentials file in environment
    env_creds_path = os.environ.get('GOOGLE_CREDENTIALS_FILE')
    
    # Try all possible credentials paths
    for credentials_file in [env_creds_path, app_creds_path]:
        if credentials_file and os.path.exists(credentials_file):
            print(f"✅ DEBUG: Found credentials file: {credentials_file}")
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