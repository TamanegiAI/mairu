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
    background_image_id: Optional[str] = None  # Drive ID of the background image to use in the template
    backup_folder_id: Optional[str] = None      # Specific Drive Folder ID for backing up generated posts

class GeneratedFileInfo(BaseModel):
    png_id: str
    slide_id: str
    name: str

class InstagramPostResponse(BaseModel):
    success: bool
    count: int
    message: str
    files: Optional[List[GeneratedFileInfo]] = None


class MonitoringConfigRequest(BaseModel):
    enabled: bool
    trigger_folder_id: str
    backup_folder_id: str
    spreadsheet_id: str
    monitoring_frequency_minutes: int
    status_column_name: Optional[str] = None # Name of the column in the spreadsheet for status updates
    
    # New fields for Instagram post generation specifics
    sheet_name: str
    slides_template_id: str
    recipient_email: str
    column_mappings: Optional[Dict[str, str]] = None  # Mapping of placeholders to column names
    process_flag_column: Optional[str] = None  # Column name to check for processing flag
    process_flag_value: Optional[str] = "yes"  # Value that indicates to process the row
    background_image_id: Optional[str] = None  # Drive ID of the background image to use in templates

class MonitoringConfigResponse(BaseModel):
    success: bool
    message: str
    job_id: Optional[str] = None # ID of the scheduled job if enabled

class MonitoringStatusResponse(BaseModel):
    is_monitoring_active: bool
    status_message: str
    last_check_timestamp: Optional[datetime] = None
    last_processed_image_name: Optional[str] = None
    last_processed_image_status: Optional[str] = None # e.g., "Detected", "Processing", "Sent", "Failed"
    last_processed_timestamp: Optional[datetime] = None
    error_message: Optional[str] = None
    current_config: Optional[MonitoringConfigRequest] = None # To send back current config with status