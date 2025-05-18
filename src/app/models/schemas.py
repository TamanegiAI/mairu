from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class ColumnInfo(BaseModel):
    index: int
    name: str
    letter: str

class SheetInfo(BaseModel):
    id: str
    name: str

class ColumnMapping(BaseModel):
    sheet_id: str
    mappings: Dict[str, str]  # placeholder -> column_name
    template_id: str

class MappingResponse(BaseModel):
    success: bool
    mapped_columns: Dict[str, str]

class DocumentGeneration(BaseModel):
    sheet_id: str
    template_id: str
    row_index: int

class EmailResponse(BaseModel):
    success: bool
    message_id: str
    thread_id: str

class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = None
    document_id: Optional[str] = None

class ScheduleEmail(EmailRequest):
    scheduled_time: datetime

class TokenInfo(BaseModel):
    token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: List[str]

class DocumentGenerationResponse(BaseModel):
    success: bool
    document_id: str
    document_title: str

class ScheduleEmailResponse(BaseModel):
    success: bool
    job_id: str
    scheduled_time: str

class ScheduledEmailInfo(BaseModel):
    job_id: str
    scheduled_time: str
    status: str

class CancelScheduledEmailResponse(BaseModel):
    success: bool
    message: str

class DriveFile(BaseModel):
    id: str
    name: str
    mimeType: str
    webViewLink: Optional[str] = None

class InstagramPostRequest(BaseModel):
    spreadsheet_id: str
    sheet_name: str
    slides_template_id: str
    drive_folder_id: str
    recipient_email: str
    column_mappings: Optional[Dict[str, str]] = None  # Mapping of placeholders to column names
    process_flag_column: Optional[str] = None  # Column name to check for processing flag
    process_flag_value: Optional[str] = "yes"  # Value that indicates to process the row

class InstagramPostResponse(BaseModel):
    success: bool
    count: int
    message: str
    files: Optional[List[str]] = None