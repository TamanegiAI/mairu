from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from dotenv import load_dotenv
import os
import sys

# Force load environment variables and verify they're loaded
load_dotenv(override=True)

# Immediately check if environment variables are present
print("🔍 DEBUG: Checking environment variables directly:")
print(f"GOOGLE_CLIENT_ID from os.environ: {os.getenv('GOOGLE_CLIENT_ID')}")
print(f"GOOGLE_CLIENT_SECRET from os.environ: {os.getenv('GOOGLE_CLIENT_SECRET')}")
print(f"GOOGLE_REDIRECT_URI from os.environ: {os.getenv('GOOGLE_REDIRECT_URI')}")

# Exit if environment variables are not set
if not all([os.getenv('GOOGLE_CLIENT_ID'), 
            os.getenv('GOOGLE_CLIENT_SECRET'), 
            os.getenv('GOOGLE_REDIRECT_URI')]):
    print("❌ ERROR: Required environment variables are not set!")
    print("Please ensure your .env file exists and contains the required variables.")
    sys.exit(1)

class Settings(BaseSettings):
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_prefix=""  # Ensure no prefix is added to env var names
    )

@lru_cache()
def get_settings() -> Settings:
    try:
        settings = Settings()
        print("\n🔍 DEBUG: Settings initialized with:")
        print(f"CLIENT_ID: {settings.google_client_id}")
        print(f"REDIRECT_URI: {settings.google_redirect_uri}")
        return settings
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize settings: {str(e)}")
        raise