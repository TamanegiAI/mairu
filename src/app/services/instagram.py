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
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

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
                      column_mappings: Optional[Dict[str, str]] = None,
                      process_flag_column: Optional[str] = None,
                      process_flag_value: str = "yes",
                      image_url: Optional[str] = None,
                      update_status_column: Optional[str] = None,
                      background_image_id: Optional[str] = None,
                      backup_folder_id: Optional[str] = None) -> Dict[str, Any]:
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
        - background_image_id: Optional Drive ID of image to use as background in slides
        - backup_folder_id: Optional ID of folder to save generated images as backup
        """
        try:
            print(f"DEBUG: generate_posts called with background_image_id='{background_image_id}', backup_folder_id='{backup_folder_id}'")
            # 1. Get data from the spreadsheet
            sheet_data = self._get_sheet_data(spreadsheet_id, sheet_name)
            if not sheet_data or len(sheet_data) <= 1:  
                return {
                    "success": False,
                    "count": 0,
                    "message": "No data found in the spreadsheet."
                }
            
            # 2. Process headers and set up column indices
            headers = sheet_data[0]  
            
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
                    status_col_idx = len(headers)
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
            
            # Determine target folder for generation outputs
            target_folder_for_generation = backup_folder_id if backup_folder_id else drive_folder_id
            if not target_folder_for_generation:
                print("CRITICAL ERROR: No target folder specified for generation (backup_folder_id or drive_folder_id required).")
                return {
                    "success": False, "count": 0,
                    "message": "A target folder (backup_folder_id or drive_folder_id) must be specified for generation output."
                }
            print(f"Using target folder for generation outputs: {target_folder_for_generation}")

            # Determine image_content: prioritize background_image_id, then image_url
            image_content = None
            print(f"DEBUG: Initial image_content is None. Checking background_image_id='{background_image_id}' and image_url='{image_url}'")
            if background_image_id:
                try:
                    if not hasattr(self, 'drive_service') or self.drive_service is None:
                        raise Exception("Drive service not initialized during image fetch.")
                    print(f"Fetching image content from Drive ID: {background_image_id}")
                    # Set the file permission to public (anyone with the link can view)
                    try:
                        self.drive_service.permissions().create(
                            fileId=background_image_id,
                            body={'type': 'anyone', 'role': 'reader'},
                        ).execute()
                        print(f"Set file permission to public for image {background_image_id}")
                    except Exception as e:
                        print(f"Warning: Could not set file permission to public: {str(e)}")
                    # Get the public URL for the image
                    file = self.drive_service.files().get(fileId=background_image_id, fields='webContentLink').execute()
                    image_url = file.get('webContentLink')
                    print(f"Using public image URL: {image_url}")
                except Exception as e:
                    print(f"DEBUG: Error preparing public image URL from Drive ID {background_image_id}: {str(e)}")
                    image_url = None
            elif image_url:
                # If image_url is provided directly, use it
                pass
            else:
                image_url = None
        
            print(f"DEBUG: image_content before loop: {'present (size: ' + str(len(image_content)) + ')' if 'image_content' in locals() and image_content else 'None'}")
            # Process each row (skip header)
            for i, row in enumerate(sheet_data[1:], 1):
                try:
                    # Check if we should process this row based on flag
                    should_process = True
                    if process_flag_idx != -1 and process_flag_idx < len(row):
                        flag_value = row[process_flag_idx] if process_flag_idx < len(row) else ""
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
                    
                    print(f"DEBUG: Row {i}: image_content passed to _generate_post_from_template: {'present (size: ' + str(len(image_content)) + ')' if 'image_content' in locals() and image_content else 'None'}")
                    # Generate post for this row
                    generation_result = self._generate_post_from_template(
                        slides_template_id,
                        text_replacements,
                        target_folder_for_generation, 
                        f"InstagramPost_{i}",
                        image_url=image_url
                    )
                    
                    if generation_result:
                        png_id, slide_id = generation_result
                        file_entry = {
                            "png_id": png_id,
                            "slide_id": slide_id,
                            "name": f"InstagramPost_{i}"
                        }
                        # Back up the original background image if applicable
                        print(f"DEBUG: Row {i}: Checking for original image backup. background_image_id='{background_image_id}', backup_folder_id='{backup_folder_id}'")
                        if background_image_id and backup_folder_id:
                            try:
                                # Fetch original image's metadata to get its name for the copy
                                original_image_meta = self.drive_service.files().get(
                                    fileId=background_image_id, fields='name'
                                ).execute()
                                original_image_name_for_copy = original_image_meta.get('name', f"Original_Background_Image_{i}")
                                
                                copy_body = {
                                    'name': original_image_name_for_copy,
                                    'parents': [backup_folder_id]
                                }
                                backed_up_original_file = self.drive_service.files().copy(
                                    fileId=background_image_id, # Source is the original background image
                                    body=copy_body,
                                    fields='id'
                                ).execute()
                                original_image_backup_id = backed_up_original_file.get('id')
                                file_entry['original_image_backup_id'] = original_image_backup_id
                                print(f"DEBUG: Row {i}: Successfully backed up original background image {background_image_id} to {original_image_backup_id} in folder {backup_folder_id} as '{original_image_name_for_copy}'")
                                
                                # Optionally: Delete original image from trigger folder after successful backup
                                # self.drive_service.files().delete(fileId=background_image_id).execute()
                                # print(f"Row {i}: Deleted original background image {background_image_id} from trigger folder.")

                            except Exception as e:
                                print(f"DEBUG: Row {i}: Error backing up original background image {background_image_id}: {str(e)}")
                        
                        generated_files.append(file_entry)
                        processed_count += 1
                        print(f"Row {i}: Generated post with file ID {png_id}")
                        if status_col_idx != -1:
                            print(f"DEBUG: Row {i}: Attempting to update status to 'Sent'")
                            self._update_cell(spreadsheet_id, sheet_name, i + 1, status_col_idx + 1, "Sent")
                            print(f"DEBUG: Row {i}: Successfully updated status to 'Sent'")
                    else: # This 'else' corresponds to 'if generation_result:'
                        skipped_count += 1
                        if status_col_idx != -1:
                            print(f"DEBUG: Row {i}: Attempting to update status to 'Failed to generate'")
                            self._update_cell(spreadsheet_id, sheet_name, i + 1, status_col_idx + 1, "Failed to generate")
                            print(f"DEBUG: Row {i}: Successfully updated status to 'Failed to generate'")
                        print(f"Row {i}: Failed to generate post")
                
                except Exception as e: # This 'except' corresponds to the 'try' at the start of the loop for this row
                    print(f"DEBUG: Error processing row {i}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    if status_col_idx != -1:
                        self._update_cell(spreadsheet_id, sheet_name, i + 1, status_col_idx + 1, f"Error: {str(e)}")
                    skipped_count += 1
            
            # 3. Send email with generated posts if any were created
            print(f"DEBUG: After loop. generated_files count: {len(generated_files)}")
            if generated_files:
                print(f"DEBUG: Attempting to send email to {recipient_email} with {len(generated_files)} attachments.")
                email_sent = self._send_email_with_attachments(
                    recipient_email,
                    "Your Instagram Posts",
                    f"Generated {len(generated_files)} Instagram posts.",
                    [file_entry['png_id'] for file_entry in generated_files] # Use the correct file ID for the PNG
                )
                
                print(f"DEBUG: Email sent status: {email_sent}")
                if not email_sent:
                    results_on_email_fail = {
                        "success": True,
                        "count": len(generated_files),
                        "message": f"Generated {len(generated_files)} Instagram posts but FAILED to send email to {recipient_email}. Check logs. Skipped {skipped_count} rows.",
                        "files": generated_files
                    }
                    print(f"DEBUG: Returning (email failed): {results_on_email_fail}")
                    return results_on_email_fail
                
                results_on_success = {
                    "success": True,
                    "count": len(generated_files),
                    "message": f"Generated {len(generated_files)} Instagram posts and sent to {recipient_email}. Skipped {skipped_count} rows.",
                    "files": generated_files
                }
                print(f"DEBUG: Returning (email success): {results_on_success}")
                return results_on_success
            else:
                results_no_files = {
                    "success": False,
                    "count": 0,
                    "message": f"No posts were generated. Skipped {skipped_count} rows. Check your mappings and flag conditions."
                }
                print(f"DEBUG: Returning (no files generated): {results_no_files}")
                return results_no_files
                
        except Exception as e:
            print(f"DEBUG: CRITICAL Error in generate_posts (main try-except): {str(e)}")
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
                                   image_url: Optional[str] = None) -> Optional[tuple[str, str]]:
        """Generate a post image from the template and save to Drive."""
        try:
            print(f"Generating post from template {template_id}")
            print(f"Text replacements: {text_replacements}")
            print(f"Target folder ID: {folder_id}")
            
            # Verify the folder ID is valid
            try:
                folder = self.drive_service.files().get(
                    fileId=folder_id,
                    fields='mimeType'
                ).execute()
                if folder.get('mimeType') != 'application/vnd.google-apps.folder':
                    raise ValueError(f"Specified ID {folder_id} is not a folder")
            except Exception as e:
                print(f"Error verifying folder ID: {str(e)}")
                raise ValueError(f"Invalid folder ID: {folder_id}. Please ensure you've selected a valid Google Drive folder.")
            
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
            
            # Replace image if image_url is provided
            if image_url:
                # First get the presentation to find images
                slides = presentation.get('slides', [])
                for i, slide in enumerate(slides):
                    slide_id = slide.get('objectId')
                    images = slide.get('pageElements', [])
                    for element in images:
                        if 'image' in element:
                            image_id = element.get('objectId')
                            # Add request to replace the image with the public URL
                            slides_requests.append({
                                'replaceImage': {
                                    'imageObjectId': image_id,
                                    'url': image_url
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
            
            png_file_id = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute().get('id') # Get the ID directly
            
            # 5. Rename the processed presentation (it's no longer temporary and is already in the correct folder_id)
            processed_slide_name = f"Processed_{file_name}_{int(time.time())}" 
            self.drive_service.files().update(
                fileId=presentation_id,
                body={'name': processed_slide_name}
            ).execute()
            print(f"Renamed processed presentation to: {processed_slide_name} (ID: {presentation_id})")
            
            return png_file_id, presentation_id
            
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
                    
                    # Fetch file content
                    request = self.drive_service.files().get_media(fileId=file_id).execute()
                    
                    # Attach to message
                    attachment = MIMEImage(request, _subtype='png')
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