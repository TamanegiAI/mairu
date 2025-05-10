from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from fastapi import HTTPException
from typing import Dict, Any

class GoogleDocsService:
    def __init__(self, access_token: str):
        try:
            credentials = Credentials(token=access_token)
            self.service = build('docs', 'v1', credentials=credentials)
        except Exception as e:
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