from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from fastapi import HTTPException
from typing import List, Dict

class GoogleSheetsService:
    def __init__(self, access_token: str):
        try:
            credentials = Credentials(token=access_token)
            self.service = build('sheets', 'v4', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
        except Exception as e:
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