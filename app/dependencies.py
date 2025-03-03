from app.config import get_settings
from app.services.auth import GoogleAuth

def get_google_auth() -> GoogleAuth:
    settings = get_settings()
    print(f"🔍 DEBUG: Creating new GoogleAuth instance")
    print(f"🔍 DEBUG: Using client_id={settings.google_client_id}")
    
    auth = GoogleAuth(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri
    )
    return auth