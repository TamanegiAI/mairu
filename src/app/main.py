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
    CancelScheduledEmailResponse,
    DriveFile,
    InstagramPostRequest,
    InstagramPostResponse,
    MonitoringConfigRequest,
    MonitoringConfigResponse,
    MonitoringStatusResponse
)
from src.app.dependencies import get_google_auth
from src.app.services.sheets import GoogleSheetsService
from src.app.services.docs import GoogleDocsService
from src.app.services.gmail import GmailService
from src.app.services.scheduler import email_scheduler
from src.app.services.drive import DriveService
from src.app.services.instagram import InstagramService
from src.app.services.monitoring_service import folder_monitoring_service
from src.app.services.token_store import TokenStore
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
        existing_tokens = TokenStore.get_latest_tokens()
        if existing_tokens and existing_tokens.get('created_at') and \
           (datetime.fromisoformat(existing_tokens.get('created_at')) > datetime.utcnow() - timedelta(minutes=1)):
            print("Recent tokens found, returning existing access token")
            return {"message": "Authentication successful", "access_token": existing_tokens.get('token')}
        
        # Clear any existing tokens before starting a new authentication flow
        # This helps prevent conflicts with existing token states
        TokenStore.clear_tokens()
        
        try:
            tokens = auth.get_tokens(code)
            print("✅ Authentication successful with token: " + tokens["token"][:15] + "...")
            return {"message": "Authentication successful", "access_token": tokens["token"]}
        except Exception as e:
            error_str = str(e)
            # We've already improved handling of scope changes in the get_tokens method,
            # but let's add an additional fallback here just in case
            if "invalid_grant" in error_str.lower():
                print(f"Warning: {error_str}")
                print("Invalid grant error, redirecting to new authentication flow")
                
                # Generate a new authorization URL for the user to try again
                auth_url = auth.get_authorization_url()
                return {
                    "message": "Please try authenticating again with a fresh authorization",
                    "retry": True,
                    "authorization_url": auth_url
                }
            else:
                raise e
            
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
            
            # Get refresh token from TokenStore to enable refresh if needed
            stored_tokens = TokenStore.get_latest_tokens()
            refresh_token = stored_tokens.get('refresh_token') if stored_tokens else None
            
            token_info = {
                'token': access_token,
                'refresh_token': refresh_token,
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': auth.client_id,
                'client_secret': auth.client_secret,
                'scopes': auth.SCOPES
            }
        
        # If no Authorization header or no token_info created, use TokenStore token
        if not token_info:
            print("🔍 Using token from TokenStore")
            stored_tokens = TokenStore.get_latest_tokens()
            if not stored_tokens:
                raise HTTPException(
                    status_code=401,
                    detail="No access token found. Please authenticate first."
                )
            
            token_info = {
                'token': stored_tokens.get('token'),
                'refresh_token': stored_tokens.get('refresh_token'),
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': auth.client_id,
                'client_secret': auth.client_secret,
                'scopes': auth.SCOPES
            }
        
        # Validate and refresh token if needed
        print("🔄 Validating token...")
        valid_token_info = await auth.validate_and_refresh_token(token_info, db)
        
        # Use the valid token to call Google Sheets API
        print(f"🔍 DEBUG: Creating GoogleSheetsService with complete token info")
        sheets_service = GoogleSheetsService(valid_token_info)
        sheets = sheets_service.list_sheets()
        print(f"✅ DEBUG: Successfully fetched {len(sheets)} sheets")
        
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
        print(f"🔍 DEBUG: get_columns called for sheet_id={sheet_id}")
        
        tokens = TokenStore.get_latest_tokens()
        if not tokens:
            print("❌ DEBUG: No tokens found in TokenStore")
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )
            
        # Check auth object
        print(f"🔍 DEBUG: Auth object client_id: {auth.client_id[:5] if auth.client_id else 'None'}")
        
        # Make sure we have client credentials
        if not auth.client_id or not auth.client_secret:
            print("❌ DEBUG: Missing client ID or client secret in auth configuration")
            # Try to use credentials from settings as fallback
            settings = get_settings()
            if settings.google_client_id and settings.google_client_secret:
                print("🔄 DEBUG: Using client credentials from settings as fallback")
                client_id = settings.google_client_id
                client_secret = settings.google_client_secret
            else:
                raise ValueError("Missing client ID or client secret in auth configuration")
        else:
            client_id = auth.client_id
            client_secret = auth.client_secret
            
        # Create token info with all required fields
        token_info = {
            'token': tokens.get('token'),
            'refresh_token': tokens.get('refresh_token'),
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': client_id,
            'client_secret': client_secret,
            'scopes': auth.SCOPES
        }
        
        # Validate and refresh token if needed
        print("🔄 DEBUG: Validating and refreshing token if needed...")
        valid_token_info = await auth.validate_and_refresh_token(token_info)
        
        # Use the valid token with sheets service
        print(f"🔍 DEBUG: Creating GoogleSheetsService with complete token info")
        sheets_service = GoogleSheetsService(valid_token_info)
        columns = sheets_service.get_columns(sheet_id)
        print(f"✅ DEBUG: Successfully fetched {len(columns)} columns")
        return columns
        
    except Exception as e:
        print(f"❌ ERROR in get_columns: {str(e)}")
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
        tokens = TokenStore.get_latest_tokens()
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
        tokens = TokenStore.get_latest_tokens()
        if not tokens:
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )
        
        # Get client credentials for token refresh
        client_id = auth.client_id
        client_secret = auth.client_secret
            
        # Create complete token info with all required fields for token refresh
        token_info = {
            'token': tokens.get('token'),
            'refresh_token': tokens.get('refresh_token'),
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': client_id,
            'client_secret': client_secret,
            'scopes': auth.SCOPES
        }
        
        # Validate and refresh token if needed
        print("🔄 DEBUG: Validating and refreshing token if needed...")
        valid_token_info = await auth.validate_and_refresh_token(token_info)
        
        # Get the sheet data with full token info for refresh capability
        sheets_service = GoogleSheetsService(valid_token_info)
        
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
        
        # Initialize Docs service with full token info for refresh capability
        docs_service = GoogleDocsService(valid_token_info)
        
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
        tokens = TokenStore.get_latest_tokens()
        if not tokens:
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )
            
        # Get client credentials for token refresh
        client_id = auth.client_id
        client_secret = auth.client_secret
            
        # Create complete token info with all required fields for token refresh
        token_info = {
            'token': tokens.get('token'),
            'refresh_token': tokens.get('refresh_token'),
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': client_id,
            'client_secret': client_secret,
            'scopes': auth.SCOPES
        }
        
        # Validate and refresh token if needed
        print("🔄 DEBUG: Validating and refreshing token if needed...")
        valid_token_info = await auth.validate_and_refresh_token(token_info)

        gmail_service = GmailService(valid_token_info)
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
        tokens = TokenStore.get_latest_tokens()
        if not tokens:
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )
            
        # Get client credentials for token refresh
        client_id = auth.client_id
        client_secret = auth.client_secret
            
        # Create complete token info with all required fields for token refresh
        token_info = {
            'token': tokens.get('token'),
            'refresh_token': tokens.get('refresh_token'),
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': client_id,
            'client_secret': client_secret,
            'scopes': auth.SCOPES
        }
        
        # Validate and refresh token if needed
        print("🔄 DEBUG: Validating and refreshing token if needed...")
        valid_token_info = await auth.validate_and_refresh_token(token_info)

        result = email_scheduler.schedule_email(
            db=db,  # Pass db to scheduler
            access_token=valid_token_info,  # Pass full token info
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

@app.get("/drive/search", response_model=List[DriveFile])
async def search_drive(
    query: str,
    file_type: str = None,
    db: Session = Depends(get_db),
    auth: GoogleAuth = Depends(get_google_auth)
):
    """Search for files in Google Drive."""
    try:
        print(f"🔍 DEBUG: search_drive called with query='{query}', file_type='{file_type}'")
        
        tokens = TokenStore.get_latest_tokens()
        if not tokens:
            print("❌ DEBUG: No tokens found in TokenStore")
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )
        
        # Get config for client credentials
        settings = get_settings()
        print(f"🔍 DEBUG: Got settings, client_id from settings: {settings.google_client_id[:5] if settings.google_client_id else 'None'}")
        
        # Check auth object
        print(f"🔍 DEBUG: Auth object client_id: {auth.client_id[:5] if auth.client_id else 'None'}")
        
        # Make sure we have client credentials
        if not auth.client_id or not auth.client_secret:
            print("❌ DEBUG: Missing client ID or client secret in auth configuration")
            # Try to use credentials from settings as fallback
            if settings.google_client_id and settings.google_client_secret:
                print("🔄 DEBUG: Using client credentials from settings as fallback")
                client_id = settings.google_client_id
                client_secret = settings.google_client_secret
            else:
                raise ValueError("Missing client ID or client secret in auth configuration")
        else:
            client_id = auth.client_id
            client_secret = auth.client_secret
            
        # Enhance token info with client credentials required for refresh
        complete_token_info = {
            'token': tokens.get('token'),
            'refresh_token': tokens.get('refresh_token'),
            'client_id': client_id,
            'client_secret': client_secret,
            'scopes': auth.SCOPES
        }
        
        print(f"🔍 DEBUG: Using client_id: {client_id[:5]}... for DriveService")
        
        # Create a new DriveService with the complete token info
        drive_service = DriveService(complete_token_info)
        files = drive_service.search_files(query, file_type)
        
        print(f"✅ DEBUG: Found {len(files)} files matching query")
        
        # Transform data for response
        return files
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search Drive files: {str(e)}"
        )

@app.post("/instagram/generate", response_model=InstagramPostResponse)
async def generate_instagram_posts(
    request: InstagramPostRequest,
    db: Session = Depends(get_db),
    auth: GoogleAuth = Depends(get_google_auth),
    authorization: Optional[str] = Header(None) # Keep Authorization header for consistency
):
    """Generate Instagram posts from spreadsheet data."""
    try:
        print(f"🔍 DEBUG: generate_instagram_posts called")
        
        tokens = TokenStore.get_latest_tokens()
        if not tokens:
            print("❌ DEBUG: No tokens found in TokenStore")
            raise HTTPException(
                status_code=401,
                detail="No access token found. Please authenticate first."
            )
        
        # Get config for client credentials
        settings = get_settings()
        print(f"🔍 DEBUG: Got settings, client_id from settings: {settings.google_client_id[:5] if settings.google_client_id else 'None'}")
        
        # Check auth object
        print(f"🔍 DEBUG: Auth object client_id: {auth.client_id[:5] if auth.client_id else 'None'}")
        
        # Make sure we have client credentials
        if not auth.client_id or not auth.client_secret:
            print("❌ DEBUG: Missing client ID or client secret in auth configuration")
            # Try to use credentials from settings as fallback
            if settings.google_client_id and settings.google_client_secret:
                print("🔄 DEBUG: Using client credentials from settings as fallback")
                client_id = settings.google_client_id
                client_secret = settings.google_client_secret
            else:
                raise ValueError("Missing client ID or client secret in auth configuration")
        else:
            client_id = auth.client_id
            client_secret = auth.client_secret
            
        # Enhance token info with client credentials required for refresh
        complete_token_info = {
            'token': tokens.get('token'),
            'refresh_token': tokens.get('refresh_token'),
            'client_id': client_id,
            'client_secret': client_secret,
            'scopes': auth.SCOPES
        }
        
        # Generate Instagram posts - pass the complete token info
        instagram_service = InstagramService(complete_token_info) # Removed db argument
        result = instagram_service.generate_posts(
            spreadsheet_id=request.spreadsheet_id,
            sheet_name=request.sheet_name,
            slides_template_id=request.slides_template_id,
            drive_folder_id=request.drive_folder_id,
            recipient_email=request.recipient_email,
            column_mappings=request.column_mappings or {},
            process_flag_column=request.process_flag_column,
            process_flag_value=request.process_flag_value or "yes",
            # image_url and update_status_column are optional in generate_posts
            # and not explicitly in InstagramPostRequest, so they will be None by default
        )
        
        # The generate_posts method returns a dict like: 
        # {"success": True/False, "count": N, "files": [...], "message": "..."}
        # We need to adapt this to InstagramPostResponse which expects count and files.
        if result.get("success"):
            return InstagramPostResponse(count=result.get("count", 0), files=result.get("files", []))
        else:
            raise HTTPException(
                status_code=500, 
                detail=result.get("message", "Failed to generate Instagram posts due to an internal error.")
            )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Instagram posts: {str(e)}"
        )


# --- Folder Monitoring Endpoints ---

@app.post("/monitoring/config", response_model=MonitoringConfigResponse)
async def configure_monitoring(
    request: MonitoringConfigRequest,
    db: Session = Depends(get_db),
    auth: GoogleAuth = Depends(get_google_auth),
    authorization: Optional[str] = Header(None)
):
    try:
        token_info = None
        if authorization and authorization.startswith("Bearer "):
            access_token = authorization.replace("Bearer ", "")
            stored_tokens = TokenStore.get_latest_tokens()
            refresh_token = stored_tokens.get('refresh_token') if stored_tokens else None
            token_info = {
                'token': access_token,
                'refresh_token': refresh_token,
                'token_uri': auth.TOKEN_URI,
                'client_id': auth.client_id,
                'client_secret': auth.client_secret,
                'scopes': auth.SCOPES
            }
        
        if not token_info:
            stored_tokens = TokenStore.get_latest_tokens()
            if not stored_tokens or not stored_tokens.get('token'):
                raise HTTPException(status_code=401, detail="Authentication required.")
            token_info = {
                'token': stored_tokens.get('token'),
                'refresh_token': stored_tokens.get('refresh_token'),
                'token_uri': auth.TOKEN_URI,
                'client_id': auth.client_id,
                'client_secret': auth.client_secret,
                'scopes': auth.SCOPES
            }

        valid_token_info = await auth.validate_and_refresh_token(token_info, db)
        if not valid_token_info or not valid_token_info.get('token'):
             raise HTTPException(status_code=401, detail="Invalid or expired token after validation.")

        result = await folder_monitoring_service.update_configuration(request, auth, valid_token_info)
        return MonitoringConfigResponse(**result)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to configure monitoring: {str(e)}")

@app.get("/monitoring/status", response_model=MonitoringStatusResponse)
async def get_monitoring_status():
    try:
        status = folder_monitoring_service.get_status()
        # Convert Pydantic model in status to dict if necessary for response model compatibility
        if status.get('current_config') and not isinstance(status['current_config'], dict):
             status['current_config'] = status['current_config'].dict()
        return MonitoringStatusResponse(**status)
    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching monitoring status: {str(e)}") 
        # Return a generic error response or a more specific one if appropriate
        return MonitoringStatusResponse(
            is_monitoring_active=False,
            status_message="Error fetching status.",
            error_message=str(e)
        )

# --- End Folder Monitoring Endpoints ---


# Add more endpoints here as needed

@app.on_event("shutdown")
def shutdown_event():
    print("Application shutdown: stopping schedulers...")
    email_scheduler.scheduler.shutdown(wait=False)
    folder_monitoring_service.shutdown() # Gracefully shutdown the monitoring scheduler
    print("Schedulers stopped.")