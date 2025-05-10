from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from fastapi import HTTPException
import os
import json

class DriveAuth:
    """Google Drive authentication and service provider."""
    
    def __init__(self, credentials_file=None, token_file=None):
        """Initialize with optional custom files."""
        self.credentials_file = credentials_file or os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        self.token_file = token_file or os.getenv('GOOGLE_TOKEN_FILE', 'token.json')
        self.scopes = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/gmail.send'
        ]
        self.service = None

    def authenticate(self):
        """Authenticate with Google Drive."""
        try:
            creds = None
            # Check if token file exists and load credentials
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)
                
            # If credentials don't exist or are invalid
            if not creds or not creds.valid:
                # If credentials are expired but we have a refresh token, refresh them
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                # Otherwise, run the auth flow to get new credentials    
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.scopes)
                    creds = flow.run_local_server(port=8000)
                
                # Save new credentials to token file for future use
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                    
            # Build Drive service with credentials
            self.service = build('drive', 'v3', credentials=creds)
            return True
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to authenticate with Google Drive: {str(e)}"
            )
    
    def get_service(self):
        """Get the authenticated Drive service."""
        if not self.service:
            self.authenticate()
        return self.service
    
    def list_files(self, folder_id=None, query=None):
        """List files in Google Drive, optionally filtering by folder or query."""
        try:
            service = self.get_service()
            
            # Build query for filtering
            query_parts = []
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            if query:
                query_parts.append(query)
            
            final_query = " and ".join(query_parts) if query_parts else None
            
            # Execute the list request
            results = service.files().list(
                q=final_query,
                pageSize=100,
                fields="files(id, name, mimeType, createdTime, modifiedTime, size, webViewLink)"
            ).execute()
            
            return results.get('files', [])
        except Exception as e:
            print(f"Error listing files: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list Drive files: {str(e)}"
            )
