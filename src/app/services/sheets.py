from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from fastapi import HTTPException
from typing import List, Dict, Union, Any

class GoogleSheetsService:
    def __init__(self, token_info_or_token: Union[str, Dict[str, Any]]):
        """Initialize the Sheets service with token information or just an access token.
        
        Args:
            token_info_or_token: Either a dictionary containing token fields like 'token',
                               'refresh_token', 'token_uri', 'client_id', 'client_secret', etc.,
                               or a string representing just the access token.
        """
        try:
            # Check if token_info_or_token is a string (simple token) or dict (full token info)
            if isinstance(token_info_or_token, str):
                # Simple token initialization without refresh capability
                print("🔍 DEBUG: Initializing GoogleSheetsService with token string only")
                credentials = Credentials(token=token_info_or_token)
            else:
                # Try to use full token info with refresh capability if available
                token_info = token_info_or_token
                
                # Extract credential components
                token = token_info.get('token') if isinstance(token_info, dict) else None
                if not token:
                    raise ValueError("Access token is required")
                
                client_id = token_info.get('client_id')
                client_secret = token_info.get('client_secret')
                refresh_token = token_info.get('refresh_token')
                
                # Check if we have enough information for refresh capabilities
                if client_id and client_secret and refresh_token:
                    # Create credentials with full refresh capabilities
                    print(f"🔍 DEBUG: Creating GoogleSheetsService with refresh capabilities, client_id: {client_id[:5]}...")
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
                    print("🔍 DEBUG: Creating GoogleSheetsService with simple token (no refresh)")
                    credentials = Credentials(token=token)
            
            # Setup request for possible token refresh if we have refresh capabilities
            if hasattr(credentials, 'refresh_token') and credentials.refresh_token:
                from google.auth.transport.requests import Request
                request = Request()
                if credentials.expired:
                    print("🔄 DEBUG: Token expired, refreshing...")
                    credentials.refresh(request)
            
            # Build the services with our credentials
            self.service = build('sheets', 'v4', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
        except Exception as e:
            print(f"❌ ERROR: Failed to initialize Google Sheets service: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Google Sheets service: {str(e)}"
            )

    def list_sheets(self) -> List[Dict]:
        try:
            # Use Drive API to list spreadsheets
            results = self.drive_service.files().list(
                q="mimeType='application/vnd.google-apps.spreadsheet'",
                fields="files(id, name)",
                pageSize=50
            ).execute()
            
            files = results.get('files', [])
            return [{'id': file['id'], 'name': file['name']} for file in files]
            
        except HttpError as e:
            raise HTTPException(
                status_code=e.resp.status,
                detail=f"Google API error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch sheets: {str(e)}"
            )

    def get_columns(self, sheet_id: str) -> List[Dict[str, str]]:
        """Get column headers from the first row of the sheet."""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='A1:ZZ1'  # Get first row (headers)
            ).execute()
            
            # Get the first row values
            headers = result.get('values', [[]])[0]
            
            # Return column info with index and name
            return [
                {
                    "index": idx,
                    "name": header,
                    "letter": chr(65 + idx)  # Convert to A, B, C, etc.
                }
                for idx, header in enumerate(headers)
                if header.strip()  # Only include non-empty headers
            ]
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch columns: {str(e)}"
            )

    def get_sheet_data(self, sheet_id: str, range_name: str = 'A1:ZZ1000') -> List[List[str]]:
        """Get data from the specified sheet."""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            return result.get('values', [])
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch sheet data: {str(e)}"
            ) 