from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from base64 import urlsafe_b64encode
from fastapi import HTTPException
from typing import Optional

class GmailService:
    def __init__(self, access_token: str):
        try:
            credentials = Credentials(token=access_token)
            self.service = build('gmail', 'v1', credentials=credentials)
        except Exception as e:
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