from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from fastapi import HTTPException
from typing import Dict, Any, Union

class GoogleDocsService:
    def __init__(self, token_info_or_token: Union[str, Dict[str, Any]]):
        """Initialize the Docs service with token information or just an access token.
        
        Args:
            token_info_or_token: Either a dictionary containing token fields like 'token',
                               'refresh_token', 'token_uri', 'client_id', 'client_secret', etc.,
                               or a string representing just the access token.
        """
        try:
            # Check if token_info_or_token is a string (simple token) or dict (full token info)
            if isinstance(token_info_or_token, str):
                # Simple token initialization without refresh capability
                print("🔍 DEBUG: Initializing GoogleDocsService with token string only")
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
                    print(f"🔍 DEBUG: Creating GoogleDocsService with refresh capabilities, client_id: {client_id[:5]}...")
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
                    print("🔍 DEBUG: Creating GoogleDocsService with simple token (no refresh)")
                    credentials = Credentials(token=token)
            
            # Setup request for possible token refresh if we have refresh capabilities
            if hasattr(credentials, 'refresh_token') and credentials.refresh_token:
                from google.auth.transport.requests import Request
                request = Request()
                if credentials.expired:
                    print("🔄 DEBUG: Token expired, refreshing...")
                    credentials.refresh(request)
            
            # Build the service with our credentials
            self.service = build('docs', 'v1', credentials=credentials)
        except Exception as e:
            print(f"❌ ERROR: Failed to initialize Google Docs service: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Google Docs service: {str(e)}"
            )
    
    def get_document(self, document_id: str) -> Dict[str, Any]:
        """Fetch document content."""
        try:
            return self.service.documents().get(documentId=document_id).execute()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch document: {str(e)}"
            )
    
    def create_document(self, title: str) -> Dict[str, str]:
        """Create a new document."""
        try:
            document = self.service.documents().create(
                body={"title": title}
            ).execute()
            return {
                "id": document.get("documentId"),
                "title": document.get("title")
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create document: {str(e)}"
            )

    def replace_text(self, document_id: str, replacements: Dict[str, str]) -> Dict[str, Any]:
        """Replace placeholders with actual values."""
        try:
            requests = []
            for placeholder, value in replacements.items():
                requests.append({
                    'replaceAllText': {
                        'containsText': {
                            'text': placeholder,
                            'matchCase': True
                        },
                        'replaceText': value
                    }
                })
            
            if requests:
                result = self.service.documents().batchUpdate(
                    documentId=document_id,
                    body={'requests': requests}
                ).execute()
                return result
            return {"message": "No replacements made"}
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to replace text: {str(e)}"
            )