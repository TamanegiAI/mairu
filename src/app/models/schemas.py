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