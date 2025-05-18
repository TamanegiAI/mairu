from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from fastapi import HTTPException
from google.auth.transport.requests import Request as GoogleRequest
import os
import json

class DriveService:
    """Google Drive service for file operations."""
    
    # MIME types for different Google file types
    MIME_TYPES = {
        'spreadsheet': 'application/vnd.google-apps.spreadsheet',
        'document': 'application/vnd.google-apps.document',
        'presentation': 'application/vnd.google-apps.presentation',
        'folder': 'application/vnd.google-apps.folder',
    }
    
    def __init__(self, token_info_or_token):
        """Initialize the Drive service with token information or just an access token.
        
        Args:
            token_info_or_token: Either a dictionary containing token fields like 'token',
                               'refresh_token', 'token_uri', 'client_id', 'client_secret', etc.,
                               or a string representing just the access token.
        """
        try:
            # Check if token_info_or_token is a string (simple token) or dict (full token info)
            if isinstance(token_info_or_token, str):
                # Simple token initialization without refresh capability
                credentials = Credentials(token=token_info_or_token)
            else:
                # Try to use full token info with refresh capability if available
                token_info = token_info_or_token
                
                # Create credentials with whatever fields are available
                # Note: We're not requiring all fields now, just using what's available
                token = token_info.get('token') if isinstance(token_info, dict) else None
                if not token:
                    raise ValueError("Access token is required")
                    
                # Check if we have refresh capabilities
                client_id = token_info.get('client_id')
                client_secret = token_info.get('client_secret')
                refresh_token = token_info.get('refresh_token')
                
                # If we have all required fields for refresh capability
                if client_id and client_secret and refresh_token:
                    # Create credentials with full refresh capabilities
                    credentials = Credentials(
                        token=token,
                        refresh_token=refresh_token,
                        token_uri='https://oauth2.googleapis.com/token',
                        client_id=client_id,
                        client_secret=client_secret,
                        scopes=token_info.get('scopes', ['https://www.googleapis.com/auth/drive'])
                    )
                else:
                    # Create simple credentials without refresh capability
                    # This will work for immediate operations but won't refresh
                    credentials = Credentials(token=token)
            
            # Setup request for possible token refresh if we have refresh capabilities
            if hasattr(credentials, 'refresh_token') and credentials.refresh_token:
                request = GoogleRequest()
                if credentials.expired:
                    credentials.refresh(request)
                    
            # Build the service with our credentials
            self.service = build('drive', 'v3', credentials=credentials)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Drive service: {str(e)}"
            )
    
    def search_files(self, query: str, file_type: str = None):
        """Search for files in Google Drive by query and optional file type."""
        try:
            # Format search query
            search_query = f"name contains '{query}' and trashed=false"
            
            # Add file type filter if specified
            if file_type and file_type.lower() in self.MIME_TYPES:
                search_query += f" and mimeType='{self.MIME_TYPES[file_type.lower()]}'"
            
            # Execute search
            results = self.service.files().list(
                q=search_query,
                spaces='drive',
                fields="files(id, name, mimeType, webViewLink)",
                pageSize=10
            ).execute()
            
            return results.get('files', [])
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to search Drive files: {str(e)}"
            )
    
    def get_file(self, file_id: str):
        """Get detailed information about a specific file."""
        try:
            return self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, webViewLink"
            ).execute()
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {str(e)}"
            )
    
    def list_files_in_folder(self, folder_id: str):
        """List files in a specific folder."""
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, webViewLink)",
                pageSize=50
            ).execute()
            
            return results.get('files', [])
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list folder contents: {str(e)}"
            )

class DriveAuth:
    """Google Drive authentication and service provider."""
    
    def __init__(self, credentials_file=None, token_file=None):
        """Initialize with optional custom files."""
        self.credentials_file = credentials_file or os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        self.token_file = token_file or os.getenv('GOOGLE_TOKEN_FILE', 'token.json')
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/presentations',
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
                    creds.refresh(GoogleRequest())
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
