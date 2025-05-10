from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from dotenv import load_dotenv
import os
import sys

# Force load environment variables
load_dotenv(override=True)

# Check for credentials file first - look in both app directory and project root
credentials_file_paths = [
    os.path.join(os.path.dirname(__file__), 'credentials.json'),  # app/credentials.json
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.json')  # /credentials.json
]
credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE')
if credentials_file:
    credentials_file_paths.insert(0, credentials_file)  # Add env-specified path first

# Find first existing credentials file
found_credentials_file = None
for path in credentials_file_paths:
    if os.path.exists(path):
        found_credentials_file = path
        break

# Immediately check auth configuration
print("🔍 DEBUG: Checking auth configuration:")
if found_credentials_file:
    print(f"✅ Found credentials file: {found_credentials_file}")
    # Add to environment so other components can use it
    os.environ['GOOGLE_CREDENTIALS_FILE'] = found_credentials_file
    # Set empty values for required fields to prevent validation errors
    os.environ['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', '')
    os.environ['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    os.environ['GOOGLE_REDIRECT_URI'] = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/callback')

# Modified settings class that makes fields optional when credential file exists
class Settings(BaseSettings):
    # Make fields optional when credentials file exists
    google_client_id: str = "" if found_credentials_file else None
    google_client_secret: str = "" if found_credentials_file else None
    google_redirect_uri: str = "http://localhost:8000/auth/callback" if found_credentials_file else None
    
    # Optional database URL with default
    database_url: str = "sqlite:///./app.db"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_prefix="",  # No prefix for env vars
        extra="ignore"  # Ignore extra fields to prevent validation errors
    )

@lru_cache()
def get_settings() -> Settings:
    try:
        settings = Settings()
        print("\n🔍 DEBUG: Settings initialized")
        if found_credentials_file:
            print(f"🔍 DEBUG: Using credentials from file: {found_credentials_file}")
        else:
            print(f"CLIENT_ID: {settings.google_client_id}")
            print(f"REDIRECT_URI: {settings.google_redirect_uri}")
            if not settings.google_client_id or not settings.google_client_secret:
                print("❌ WARNING: Missing Google OAuth credentials in settings")
        return settings
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize settings: {str(e)}")
        raise