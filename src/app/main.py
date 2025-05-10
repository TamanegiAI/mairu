from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from src.app.config import get_settings
from src.app.services.auth import GoogleAuth
from src.app.models.schemas import (
    ColumnMapping,
    DocumentGeneration,
    EmailRequest,
    ScheduleEmail,
    TokenInfo,
    ColumnInfo,
    SheetInfo,
    MappingResponse,
    EmailResponse,
    ScheduleEmailResponse,
    ScheduledEmailInfo,
    CancelScheduledEmailResponse
)
from src.app.dependencies import get_google_auth
from src.app.services.sheets import GoogleSheetsService
from src.app.services.docs import GoogleDocsService
from src.app.services.gmail import GmailService
from src.app.services.scheduler import email_scheduler
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.app.database import get_db
from src.app.services.database import DatabaseService

# Try to load .env from multiple locations
env_paths = [
    os.path.join(os.path.dirname(__file__), '.env'),  # app/.env
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')  # /.env
]

for env_path in env_paths:
    if os.path.exists(env_path):
        print(f"Loading environment from: {env_path}")
        load_dotenv(env_path)
        break

app = FastAPI(title="Google Docs Automation API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/auth/url")
async def get_auth_url(auth: GoogleAuth = Depends(get_google_auth)):
    return {"authorization_url": auth.get_authorization_url()}

@app.get("/oauth2callback")
async def auth_callback(
    code: str,
    db: Session = Depends(get_db),
    auth: GoogleAuth = Depends(get_google_auth)
):
    try:
        print(f"Processing auth code: {code[:10]}...")
        
        # Check if we already have recent tokens
        existing_tokens = DatabaseService.get_latest_tokens(db)
        if existing_tokens and (datetime.utcnow() - existing_tokens.created_at).total_seconds() < 60:
            print("Recent tokens found, returning existing access token")
            return {"message": "Authentication successful", "access_token": existing_tokens.access_token}
        
        tokens = auth.get_tokens(code)
        
        # Store tokens in the database
        DatabaseService.save_tokens(
            db,
            access_token=tokens["token"],
            refresh_token=tokens["refresh_token"],
            expiry=datetime.utcnow() + timedelta(hours=1)  # Set explicit expiry
        )
        
        return {"message": "Authentication successful", "access_token": tokens["token"]}
    except Exception as e:
        print(f"Auth callback error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
        )

@app.get("/sheets", response_model=List[SheetInfo])
async def list_sheets(
    db: Session = Depends(get_db),
    auth: GoogleAuth = Depends(get_google_auth),
    authorization: Optional[str] = Header(None)
):
    try:
        token_info = None
        
        # First try to use the token from the Authorization header
        if authorization and authorization.startswith("Bearer "):
            access_token = authorization.replace("Bearer ", "")
            print("🔍 Using token from Authorization header")
            
            # Get refresh token from database to enable refresh if needed
            stored_tokens = DatabaseService.get_latest_tokens(db)
            refresh_token = stored_tokens.refresh_token if stored_tokens else None
            
            token_info = {
                'token': access_token,
                'refresh_token': refresh_token,
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': auth.client_id,
                'client_secret': auth.client_secret,
                'scopes': auth.SCOPES
            }
        
        # If no Authorization header or no token_info created, use database token
        if not token_info:
            print("🔍 Using token from database")
            stored_tokens = DatabaseService.get_latest_tokens(db)
            if not stored_tokens:
                raise HTTPException(
                    status_code=401,
                    detail="No access token found. Please authenticate first."
                )
            
            token_info = {
                'token': stored_tokens.access_token,
                'refresh_token': stored_tokens.refresh_token,
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': auth.client_id,
                'client_secret': auth.client_secret,
                'scopes': auth.SCOPES
            }
        
        # Validate and refresh token if needed
        print("🔄 Validating token...")
        valid_token_info = await auth.validate_and_refresh_token(token_info, db)
        
        # Use the valid token to call Google Sheets API
        sheets_service = GoogleSheetsService(valid_token_info['token'])
        sheets = sheets_service.list_sheets()
        
        return sheets
        
    except HTTPException as he:
        # Re-raise HTTP exceptions as is
        raise he
    except Exception as e:
        print(f"❌ Error in list_sheets: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sheets: {str(e)}"
        )

@app.get("/columns/{sheet_id}", response_model=List[ColumnInfo])
async def get_columns(
    sheet_id: str,
    db: Session = Depends(get_db),
    auth: GoogleAuth = Depends(get_google_auth)
):
    try:
        tokens = DatabaseService.get_latest_tokens(db)
        if not tokens:
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )
            
        sheets_service = GoogleSheetsService(tokens.access_token)
        columns = sheets_service.get_columns(sheet_id)
        return columns
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get columns: {str(e)}"
        )

@app.post("/map_columns", response_model=MappingResponse)
async def map_columns(
    mapping: ColumnMapping,
    db: Session = Depends(get_db),
    auth: GoogleAuth = Depends(get_google_auth)
):
    try:
        tokens = DatabaseService.get_latest_tokens(db)
        if not tokens:
            raise HTTPException(
            status_code=401,
            detail="No access token found. Please authenticate first."
            )
            
        # Store the mapping in the database
        DatabaseService.save_column_mapping(
            db,
            sheet_id=mapping.sheet_id,
            template_id=mapping.template_id,
            mappings=mapping.mappings
        )
        
        return MappingResponse(
            success=True,
            mapped_columns=mapping.mappings
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to map columns: {str(e)}"
        )

@app.post("/generate_document")
async def generate_document(
    request: DocumentGeneration,
    db: Session = Depends(get_db),
    auth: GoogleAuth = Depends(get_google_auth)
):
    try:
        tokens = DatabaseService.get_latest_tokens(db)
        if not tokens:
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )
        
        # Get the sheet data
        sheets_service = GoogleSheetsService(tokens.access_token)
        
        # Get all data from the sheet
        sheet_data = sheets_service.get_sheet_data(request.sheet_id)
        if not sheet_data or len(sheet_data) <= request.row_index:
            raise HTTPException(
                status_code=400,
                detail="Invalid row index or empty sheet"
            )
        
        # Get headers and the specified row
        headers = sheet_data[0]
        row_data = sheet_data[request.row_index]
        
        # Create a mapping of column names to values
        data_mapping = dict(zip(headers, row_data))
        
        # Initialize Docs service
        docs_service = GoogleDocsService(tokens.access_token)
        
        # Create a new document based on the template
        template_doc = docs_service.get_document(request.template_id)
        new_doc = docs_service.create_document(f"Generated - {template_doc.get('title', 'Document')}")
        
        # Copy content from template to new document
        docs_service.replace_text(
            new_doc["id"],
            {
                "{{" + header + "}}": value
                for header, value in data_mapping.items()
            }
        )
        
        return {
            "success": True,
            "document_id": new_doc["id"],
            "document_title": new_doc["title"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate document: {str(e)}"
        )

@app.post("/send_email", response_model=EmailResponse)
async def send_email(
    request: EmailRequest,
    db: Session = Depends(get_db),
    auth: GoogleAuth = Depends(get_google_auth)
):
    try:
        tokens = DatabaseService.get_latest_tokens(db)
        if not tokens:
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )

        gmail_service = GmailService(tokens.access_token)
        result = gmail_service.send_email(
            to=request.to,
            subject=request.subject,
            body=request.body,
            cc=request.cc,
            document_id=request.document_id
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email: {str(e)}"
        )

@app.post("/schedule_email", response_model=ScheduleEmailResponse)
async def schedule_email(
    request: ScheduleEmail,
    db: Session = Depends(get_db),
    auth: GoogleAuth = Depends(get_google_auth)
):
    try:
        tokens = DatabaseService.get_latest_tokens(db)
        if not tokens:
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )

        result = email_scheduler.schedule_email(
            db=db,  # Pass db to scheduler
            access_token=tokens.access_token,
            to=request.to,
            subject=request.subject,
            body=request.body,
            scheduled_time=request.scheduled_time,
            cc=request.cc,
            document_id=request.document_id
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to schedule email: {str(e)}"
        )

@app.get("/scheduled_emails", response_model=List[ScheduledEmailInfo])
async def list_scheduled_emails(auth: GoogleAuth = Depends(get_google_auth)):
    return email_scheduler.list_scheduled_emails()

@app.delete("/scheduled_emails/{job_id}", response_model=CancelScheduledEmailResponse)
async def cancel_scheduled_email(
    job_id: str,
    auth: GoogleAuth = Depends(get_google_auth)
):
    result = email_scheduler.cancel_scheduled_email(job_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result

@app.post("/auth/refresh")
async def refresh_token(
    token_info: TokenInfo,
    db: Session = Depends(get_db),
    auth: GoogleAuth = Depends(get_google_auth)
):
    try:
        new_tokens = auth.refresh_token(token_info.dict())
        return new_tokens
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token refresh failed: {str(e)}"
        )