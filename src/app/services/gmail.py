from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from base64 import urlsafe_b64encode
from fastapi import HTTPException
from typing import Optional, Dict, Any, Union

class GmailService:
    def __init__(self, token_info_or_token: Union[str, Dict[str, Any]]):
        """Initialize the Gmail service with token information or just an access token.
        
        Args:
            token_info_or_token: Either a dictionary containing token fields like 'token',
                               'refresh_token', 'token_uri', 'client_id', 'client_secret', etc.,
                               or a string representing just the access token.
        """
        try:
            # Check if token_info_or_token is a string (simple token) or dict (full token info)
            if isinstance(token_info_or_token, str):
                # Simple token initialization without refresh capability
                print("🔍 DEBUG: Initializing GmailService with token string only")
                credentials = Credentials(token=token_info_or_token)
            else:
                # Try to use full token info with refresh capability if available
                token_info = token_info_or_token
                
                # Extract credential components
                token = token_info.get('token') if isinstance(token_info, dict) else None
                if not token:
                    raise ValueError("Access token is required")
                
                client_id = token_info.get('client_id')
                client_secret = token_info.get('client_secret')
                refresh_token = token_info.get('refresh_token')
                
                # Check if we have enough information for refresh capabilities
                if client_id and client_secret and refresh_token:
                    # Create credentials with full refresh capabilities
                    print(f"🔍 DEBUG: Creating GmailService with refresh capabilities, client_id: {client_id[:5]}...")
                    credentials = Credentials(
                        token=token,
                        refresh_token=refresh_token,
                        token_uri='https://oauth2.googleapis.com/token',
                        client_id=client_id,
                        client_secret=client_secret,
                        scopes=token_info.get('scopes', ['https://www.googleapis.com/auth/gmail.send'])
                    )
                else:
                    # Create simple credentials without refresh capability
                    print("🔍 DEBUG: Creating GmailService with simple token (no refresh)")
                    credentials = Credentials(token=token)
            
            # Setup request for possible token refresh if we have refresh capabilities
            if hasattr(credentials, 'refresh_token') and credentials.refresh_token:
                from google.auth.transport.requests import Request
                request = Request()
                if credentials.expired:
                    print("🔄 DEBUG: Token expired, refreshing...")
                    credentials.refresh(request)
            
            # Build the service with our credentials
            self.service = build('gmail', 'v1', credentials=credentials)
        except Exception as e:
            print(f"❌ ERROR: Failed to initialize Gmail service: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Gmail service: {str(e)}"
            )

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> dict:
        try:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            if cc:
                message['cc'] = cc

            # Add body
            message.attach(MIMEText(body, 'html'))

            # If document_id is provided, add link to the document
            if document_id:
                doc_link = f"https://docs.google.com/document/d/{document_id}/edit"
                doc_link_html = f'<p>View the generated document: <a href="{doc_link}">Click here</a></p>'
                message.attach(MIMEText(doc_link_html, 'html'))

            # Encode the message
            encoded_message = urlsafe_b64encode(message.as_bytes()).decode()

            # Send the email
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': encoded_message}
            ).execute()

            return {
                "success": True,
                "message_id": sent_message['id'],
                "thread_id": sent_message['threadId']
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send email: {str(e)}"
            )