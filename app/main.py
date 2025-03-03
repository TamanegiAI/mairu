from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.services.auth import GoogleAuth
from app.models.schemas import (
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
from app.dependencies import get_google_auth
from app.services.sheets import GoogleSheetsService
from app.services.docs import GoogleDocsService
from app.services.gmail import GmailService
from app.services.scheduler import email_scheduler
from typing import List
from datetime import datetime

app = FastAPI(title="Google Docs Automation API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global storage for tokens (replace with proper database in production)
fake_db = {}

@app.get("/auth/url")
async def get_auth_url(auth: GoogleAuth = Depends(get_google_auth)):
    return {"authorization_url": auth.get_authorization_url()}

@app.get("/auth/callback")
async def auth_callback(code: str, auth: GoogleAuth = Depends(get_google_auth)):
    tokens = auth.get_tokens(code)
    
    # Store tokens in the global fake_db
    global fake_db  # Use the global fake_db
    fake_db["access_token"] = tokens["token"]
    fake_db["refresh_token"] = tokens["refresh_token"]
    
    print(f"🔍 DEBUG: Stored access token in fake_db: {fake_db['access_token'][:20]}...")  # Debug print
    
    return {"message": "Authentication successful", "access_token": tokens["token"]}

@app.get("/sheets", response_model=List[SheetInfo])
async def list_sheets(auth: GoogleAuth = Depends(get_google_auth)):
    try:
        if "access_token" not in fake_db:
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )
            
        sheets_service = GoogleSheetsService(fake_db["access_token"])
        sheets = sheets_service.list_sheets()
        return sheets
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sheets: {str(e)}"
        )

@app.get("/columns/{sheet_id}", response_model=List[ColumnInfo])
async def get_columns(
    sheet_id: str,
    auth: GoogleAuth = Depends(get_google_auth)
):
    try:
        if "access_token" not in fake_db:
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )
            
        sheets_service = GoogleSheetsService(fake_db["access_token"])
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
    auth: GoogleAuth = Depends(get_google_auth)
):
    try:
        if "access_token" not in fake_db:
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )
            
        # Here you would typically:
        # 1. Validate that the columns exist in the sheet
        # 2. Validate that the template exists
        # 3. Store the mapping for later use in document generation
        
        # For now, we'll just echo back the mapping
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
    auth: GoogleAuth = Depends(get_google_auth)
):
    try:
        if "access_token" not in fake_db:
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )
        
        # Get the sheet data
        sheets_service = GoogleSheetsService(fake_db["access_token"])
        
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
        docs_service = GoogleDocsService(fake_db["access_token"])
        
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
    auth: GoogleAuth = Depends(get_google_auth)
):
    try:
        if "access_token" not in fake_db:
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )

        gmail_service = GmailService(fake_db["access_token"])
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
    auth: GoogleAuth = Depends(get_google_auth)
):
    try:
        if "access_token" not in fake_db:
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )

        result = email_scheduler.schedule_email(
            access_token=fake_db["access_token"],
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