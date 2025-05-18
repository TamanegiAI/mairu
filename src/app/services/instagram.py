from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from fastapi import HTTPException
from typing import List, Dict, Any, Optional
import time
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import io
import requests
from googleapiclient.http import MediaIoBaseUpload

class InstagramService:
    """Service for generating Instagram posts from Google Sheets data using Slides templates."""
    
    def __init__(self, token_info_or_token):
        """Initialize services with an access token or token info dictionary."""
        try:
            # Handle both string token and token info dictionary
            if isinstance(token_info_or_token, str):
                # Just a token string was passed
                token = token_info_or_token
                credentials = Credentials(token=token)
                # Store the token for later use with export requests
                self.access_token = token
            else:
                # A token info dictionary was passed
                token_info = token_info_or_token
                token = token_info.get('token')
                
                if not token:
                    raise ValueError("Access token is required")
                
                # Extract credential components
                client_id = token_info.get('client_id')
                client_secret = token_info.get('client_secret')
                refresh_token = token_info.get('refresh_token')
                
                # Check if we have enough information for refresh capabilities
                if client_id and client_secret and refresh_token:
                    # Create credentials with full refresh capabilities
                    credentials = Credentials(
                        token=token,
                        refresh_token=refresh_token,
                        token_uri='https://oauth2.googleapis.com/token',
                        client_id=client_id,
                        client_secret=client_secret,
                        scopes=token_info.get('scopes', ['https://www.googleapis.com/auth/drive'])
                    )
                    print(f"Debug: Created credentials with client_id: {client_id[:5]}...")
                else:
                    # Create simple credentials without refresh capability
                    credentials = Credentials(token=token)
                    print("Debug: Created simple credentials without refresh capability")
                
                # Store the token for later use with export requests
                self.access_token = token
            
            # Setup request for possible token refresh if we have refresh capabilities
            if hasattr(credentials, 'refresh_token') and credentials.refresh_token:
                from google.auth.transport.requests import Request
                request = Request()
                if credentials.expired:
                    credentials.refresh(request)
            
            # Initialize the services
            self.sheets_service = build('sheets', 'v4', credentials=credentials)
            self.slides_service = build('slides', 'v1', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
            self.gmail_service = build('gmail', 'v1', credentials=credentials)
            
        except Exception as e:
            print(f"Error initializing Google services: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Google services: {str(e)}"
            )
    
    def generate_posts(self, 
                      spreadsheet_id: str,
                      sheet_name: str,
                      slides_template_id: str,
                      drive_folder_id: str,
                      recipient_email: str,
                      column_mappings: Dict[str, str] = None,
                      process_flag_column: str = None,
                      process_flag_value: str = "yes",
                      image_url: str = None,
                      update_status_column: str = None) -> Dict[str, Any]:
        """
        Generate Instagram posts from spreadsheet data using a Slides template.
        
        Parameters:
        - spreadsheet_id: ID of the Google Sheet
        - sheet_name: Name of the sheet tab
        - slides_template_id: ID of the Google Slides template
        - drive_folder_id: ID of folder to save generated images
        - recipient_email: Email to send generated posts to
        - column_mappings: Dictionary mapping slide placeholders to sheet column names
        - process_flag_column: Name of column to check for processing flag
        - process_flag_value: Value in flag column that indicates row should be processed
        - image_url: Optional URL of image to replace placeholder images in slides
        - update_status_column: Optional column name to update with processing status
        """
        try:
            # 1. Get data from the spreadsheet
            sheet_data = self._get_sheet_data(spreadsheet_id, sheet_name)
            if not sheet_data or len(sheet_data) <= 1:  # Check if there's data beyond header row
                return {
                    "success": False,
                    "count": 0,
                    "message": "No data found in the spreadsheet."
                }
            
            # 2. Process headers and set up column indices
            headers = sheet_data[0]  # First row contains headers
            
            # Set up column mappings
            mapping_indices = {}
            if column_mappings:
                for placeholder, column_name in column_mappings.items():
                    col_index = self._find_column_index(headers, column_name)
                    if col_index != -1:
                        mapping_indices[placeholder] = col_index
                    else:
                        print(f"Warning: Column '{column_name}' not found for placeholder '{placeholder}'")
            else:
                # Default to Japanese column if no mapping provided
                japanese_idx = self._find_column_index(headers, "Japanese")
                if japanese_idx != -1:
                    mapping_indices["{{TEXT}}"] = japanese_idx
                else:
                    print(f"Warning: No Japanese column found for default mapping")
            
            # Set up processing flag index if specified
            process_flag_idx = -1
            if process_flag_column:
                process_flag_idx = self._find_column_index(headers, process_flag_column)
                if process_flag_idx == -1:
                    print(f"Warning: Flag column '{process_flag_column}' not found")
            
            # Set up status column index if specified
            status_col_idx = -1
            if update_status_column:
                status_col_idx = self._find_column_index(headers, update_status_column)
                if status_col_idx == -1:
                    # If column doesn't exist, default to column after the last one
                    status_col_idx = len(headers)
                    # Add the status column header
                    self._update_cell(spreadsheet_id, sheet_name, 1, status_col_idx + 1, "Status")
            
            # Validate we have at least one mapping
            if not mapping_indices:
                return {
                    "success": False,
                    "count": 0,
                    "message": "No valid column mappings found."
                }
            
            # Track generated files
            generated_files = []
            processed_count = 0
            skipped_count = 0
            
            # Fetch image if URL is provided
            image_content = None
            if image_url:
                try:
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        image_content = response.content
                        print(f"Successfully fetched image from {image_url}")
                    else:
                        print(f"Failed to fetch image from {image_url}: {response.status_code}")
                except Exception as e:
                    print(f"Error fetching image from {image_url}: {str(e)}")
            
            # Process each row (skip header)
            for i, row in enumerate(sheet_data[1:], 1):
                try:
                    # Check if we should process this row based on flag
                    should_process = True
                    if process_flag_idx != -1 and process_flag_idx < len(row):
                        flag_value = row[process_flag_idx] if process_flag_idx < len(row) else ""
                        # Fix: Trim whitespace from flag values before comparison
                        should_process = (flag_value.lower().strip() == process_flag_value.lower().strip())
                        print(f"Row {i}: Flag value '{flag_value}', should process: {should_process}")
                    
                    if not should_process:
                        skipped_count += 1
                        if status_col_idx != -1:
                            self._update_cell(spreadsheet_id, sheet_name, i + 1, status_col_idx + 1, "Skipped")
                        continue
                    
                    # Prepare text replacements for this row
                    text_replacements = {}
                    has_content = False
                    for placeholder, col_idx in mapping_indices.items():
                        if col_idx < len(row) and row[col_idx] and row[col_idx].strip() != "":
                            text_replacements[placeholder] = row[col_idx]
                            has_content = True
                            print(f"Row {i}: Replacing '{placeholder}' with '{row[col_idx]}'")
                    
                    # Skip if no content found in any mapped columns
                    if not has_content:
                        skipped_count += 1
                        if status_col_idx != -1:
                            self._update_cell(spreadsheet_id, sheet_name, i + 1, status_col_idx + 1, "No content")
                        print(f"Row {i}: No content in mapped columns, skipping")
                        continue
                    
                    # Update status to processing
                    if status_col_idx != -1:
                        self._update_cell(spreadsheet_id, sheet_name, i + 1, status_col_idx + 1, "Processing...")
                    
                    # Generate post for this row
                    file_id = self._generate_post_from_template(
                        slides_template_id, 
                        text_replacements,
                        drive_folder_id,
                        f"InstagramPost_{i}",
                        image_content
                    )
                    
                    if file_id:
                        generated_files.append(file_id)
                        processed_count += 1
                        print(f"Row {i}: Generated post with file ID {file_id}")
                        if status_col_idx != -1:
                            self._update_cell(spreadsheet_id, sheet_name, i + 1, status_col_idx + 1, "Sent")
                    else:
                        skipped_count += 1
                        if status_col_idx != -1:
                            self._update_cell(spreadsheet_id, sheet_name, i + 1, status_col_idx + 1, "Failed to generate")
                        print(f"Row {i}: Failed to generate post")
                        
                except Exception as e:
                    print(f"Error processing row {i}: {str(e)}")
                    if status_col_idx != -1:
                        self._update_cell(spreadsheet_id, sheet_name, i + 1, status_col_idx + 1, f"Error: {str(e)}")
                    skipped_count += 1
            
            # 3. Send email with generated posts if any were created
            if generated_files:
                email_sent = self._send_email_with_attachments(
                    recipient_email,
                    "Your Instagram Posts",
                    f"Generated {len(generated_files)} Instagram posts.",
                    generated_files
                )
                
                if not email_sent:
                    return {
                        "success": True,
                        "count": len(generated_files),
                        "message": f"Generated {len(generated_files)} Instagram posts but FAILED to send email to {recipient_email}. Check logs. Skipped {skipped_count} rows.",
                        "files": generated_files
                    }
                
                return {
                    "success": True,
                    "count": len(generated_files),
                    "message": f"Generated {len(generated_files)} Instagram posts and sent to {recipient_email}. Skipped {skipped_count} rows.",
                    "files": generated_files
                }
            else:
                return {
                    "success": False,
                    "count": 0,
                    "message": f"No posts were generated. Skipped {skipped_count} rows. Check your mappings and flag conditions."
                }
                
        except Exception as e:
            print(f"Error in generate_posts: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate Instagram posts: {str(e)}"
            )
    
    def _update_cell(self, spreadsheet_id: str, sheet_name: str, row: int, col: int, value: str):
        """Update a specific cell in the sheet."""
        try:
            range_name = f"{sheet_name}!R{row}C{col}"
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": [[value]]}
            ).execute()
        except Exception as e:
            print(f"Error updating cell: {str(e)}")
    
    def _get_sheet_data(self, spreadsheet_id: str, sheet_name: str) -> List[List[str]]:
        """Get data from a specific sheet in a spreadsheet."""
        try:
            range_name = f"{sheet_name}"
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name
            ).execute()
            return result.get('values', [])
        except HttpError as e:
            if e.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Sheet '{sheet_name}' not found in spreadsheet."
                )
            raise HTTPException(
                status_code=e.status_code,
                detail=f"Error accessing spreadsheet: {str(e)}"
            )
    
    def _find_column_index(self, headers: List[str], column_name: str) -> int:
        """Find the index of a column by name (case-insensitive partial match)."""
        for i, header in enumerate(headers):
            if column_name.lower() in header.lower():
                return i
        return -1
    
    def _generate_post_from_template(self, 
                                   template_id: str,
                                   text_replacements: Dict[str, str],
                                   folder_id: str,
                                   file_name: str,
                                   image_content: Optional[bytes] = None) -> Optional[str]:
        """Generate a post image from the template and save to Drive."""
        try:
            print(f"Generating post from template {template_id}")
            print(f"Text replacements: {text_replacements}")
            
            # 1. Copy the template slide to a new presentation
            new_presentation = self.drive_service.files().copy(
                fileId=template_id,
                body={"name": f"Temp_{file_name}", "parents": [folder_id]}
            ).execute()
            presentation_id = new_presentation['id']
            print(f"Created temporary presentation with ID: {presentation_id}")
            
            # 2. Get the slide IDs in the presentation
            presentation = self.slides_service.presentations().get(
                presentationId=presentation_id
            ).execute()
            
            if not presentation.get('slides'):
                raise Exception(f"No slides found in template presentation {template_id}")
            
            # 2. Replace text placeholders in the slide
            slides_requests = []
            
            # Add text replacement requests
            for placeholder, replacement_text in text_replacements.items():
                # Create the text replacement request without matching case
                slides_requests.append({
                    'replaceAllText': {
                        'containsText': {
                            'text': placeholder,
                            'matchCase': False
                        },
                        'replaceText': replacement_text
                    }
                })
            
            # Replace image if image content is provided
            if image_content:
                # First get the presentation to find images
                slides = presentation.get('slides', [])
                for i, slide in enumerate(slides):
                    slide_id = slide.get('objectId')
                    images = slide.get('pageElements', [])
                    
                    for element in images:
                        if 'image' in element:
                            image_id = element.get('objectId')
                            
                            # Add request to replace the image
                            slides_requests.append({
                                'replaceImage': {
                                    'imageObjectId': image_id,
                                    'url': f"data:image/jpeg;base64,{base64.b64encode(image_content).decode('utf-8')}"
                                }
                            })
                            print(f"Found image to replace in slide {i+1}")
                            break
            
            if slides_requests:
                update_result = self.slides_service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={'requests': slides_requests}
                ).execute()
                print(f"Text replacement result: {update_result}")
            
            # Wait for changes to propagate
            time.sleep(2)
            
            # 3. Export the slide as PNG
            export_url = f"https://docs.google.com/presentation/d/{presentation_id}/export/png"
            response = requests.get(export_url, headers={
                "Authorization": f"Bearer {self.access_token}"
            })
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to export slide as PNG: {response.text}"
                )
            
            # 4. Save the PNG to Drive
            file_metadata = {
                'name': f"{file_name}.png",
                'parents': [folder_id],
                'mimeType': 'image/png'
            }
            
            media = MediaIoBaseUpload(
                io.BytesIO(response.content),
                mimetype='image/png',
                resumable=True
            )
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            # 5. Delete the temporary presentation
            self.drive_service.files().delete(fileId=presentation_id).execute()
            
            return file.get('id')
            
        except Exception as e:
            print(f"Error generating post from template: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _send_email_with_attachments(self, 
                                 to: str,
                                 subject: str,
                                 body: str,
                                 file_ids: List[str]) -> bool:
        """Send an email with Drive file attachments."""
        try:
            print(f"Sending email to {to} with {len(file_ids)} attachments")
            
            # Create multipart message
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            # Add body
            msg_text = MIMEText(body)
            message.attach(msg_text)
            
            # Attach files
            for file_id in file_ids:
                try:
                    # Get file metadata
                    file = self.drive_service.files().get(fileId=file_id, fields="name").execute()
                    file_name = file.get('name', f"file_{file_id}")
                    
                    # Get the file content directly
                    file_content = self.drive_service.files().get_media(fileId=file_id).execute()
                    
                    # Attach to message
                    attachment = MIMEImage(file_content, _subtype='png')
                    attachment.add_header('Content-Disposition', f'attachment; filename="{file_name}"')
                    attachment.add_header('X-Attachment-Id', file_id)
                    attachment.add_header('Content-ID', f'<{file_id}>')
                    message.attach(attachment)
                    print(f"Attached file {file_name}")
                except Exception as e:
                    print(f"Error attaching file {file_id}: {str(e)}")
            
            # Encode and send message
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_message = self.gmail_service.users().messages().send(
                userId='me', 
                body={'raw': encoded_message}
            ).execute()
            
            print(f"Email sent with message ID: {send_message.get('id')}")
            return True
            
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            import traceback
            traceback.print_exc()
            return False