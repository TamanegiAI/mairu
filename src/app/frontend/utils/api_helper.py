# src/app/frontend/utils/api_helper.py

import requests
import streamlit as st
import json
from typing import List, Dict, Any, Optional

# API base URL (local development)
API_BASE_URL = "http://localhost:8000"

def get_auth_url() -> str:
    """Get the Google OAuth authorization URL"""
    try:
        response = requests.get(f"{API_BASE_URL}/auth/url")
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()
        
        # Add debugging to see what's actually in the response
        print(f"Auth URL response: {data}")
        
        if "authorization_url" in data:
            return data["authorization_url"]
        else:
            st.error(f"Missing authorization_url in response. Response: {data}")
            return ""
    except requests.exceptions.RequestException as e:
        st.error(f"Request error: {str(e)}")
        return ""
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON response: {str(e)}")
        return ""
    except Exception as e:
        st.error(f"Failed to get authentication URL: {str(e)}")
        return ""

def process_auth_callback(code: str) -> Dict[str, Any]:
    """Process authentication callback with authorization code"""
    try:
        response = requests.get(f"{API_BASE_URL}/oauth2callback?code={code}")
        if response.status_code == 200:
            data = response.json()
            st.session_state.access_token = data.get("access_token")
            st.session_state.is_authenticated = True
            return {"success": True, "message": "Authentication successful"}
        else:
            return {"success": False, "message": f"Authentication failed: {response.text}"}
    except Exception as e:
        return {"success": False, "message": f"Authentication error: {str(e)}"}

def get_sheets(access_token: str) -> List[Dict[str, str]]:
    """Get list of user's Google Sheets"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/sheets",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch sheets: {response.text}")
            return []
    except Exception as e:
        st.error(f"Error fetching sheets: {str(e)}")
        return []

def get_sheet_columns(sheet_id: str, access_token: str) -> List[Dict[str, Any]]:
    """Get columns from a specific sheet"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/columns/{sheet_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch columns: {response.text}")
            return []
    except Exception as e:
        st.error(f"Error fetching columns: {str(e)}")
        return []

def save_mapping(sheet_id: str, template_id: str, mappings: Dict[str, str], access_token: str) -> Dict[str, Any]:
    """Save column mappings"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/map_columns",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "sheet_id": sheet_id,
                "template_id": template_id,
                "mappings": mappings
            }
        )
        return response.json()
    except Exception as e:
        st.error(f"Error saving mappings: {str(e)}")
        return {"success": False, "message": str(e)}

def generate_document(sheet_id: str, template_id: str, row_index: int, access_token: str) -> Dict[str, Any]:
    """Generate a document from template using sheet data"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate_document",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "sheet_id": sheet_id,
                "template_id": template_id,
                "row_index": row_index
            }
        )
        return response.json()
    except Exception as e:
        st.error(f"Error generating document: {str(e)}")
        return {"success": False, "message": str(e)}

def send_email(to: str, subject: str, body: str, access_token: str, 
              cc: Optional[str] = None, document_id: Optional[str] = None) -> Dict[str, Any]:
    """Send an email, optionally with document link"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/send_email",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "to": to,
                "subject": subject,
                "body": body,
                "cc": cc,
                "document_id": document_id
            }
        )
        return response.json()
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return {"success": False, "message": str(e)}

def schedule_email(to: str, subject: str, body: str, scheduled_time: str, 
                 access_token: str, cc: Optional[str] = None, 
                 document_id: Optional[str] = None) -> Dict[str, Any]:
    """Schedule an email to be sent later"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/schedule_email",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "to": to,
                "subject": subject,
                "body": body,
                "cc": cc,
                "document_id": document_id,
                "scheduled_time": scheduled_time
            }
        )
        return response.json()
    except Exception as e:
        st.error(f"Error scheduling email: {str(e)}")
        return {"success": False, "message": str(e)}

def get_scheduled_emails(access_token: str) -> List[Dict[str, Any]]:
    """Get list of scheduled emails"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/scheduled_emails",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        return response.json()
    except Exception as e:
        st.error(f"Error fetching scheduled emails: {str(e)}")
        return []

def cancel_scheduled_email(job_id: str, access_token: str) -> Dict[str, Any]:
    """Cancel a scheduled email"""
    try:
        response = requests.delete(
            f"{API_BASE_URL}/scheduled_emails/{job_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        return response.json()
    except Exception as e:
        st.error(f"Error canceling email: {str(e)}")
        return {"success": False, "message": str(e)}

def search_drive_files(query: str, file_type: str, access_token: str) -> List[Dict[str, Any]]:
    """Search for files in Google Drive by query and type"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/drive/search",
            params={"query": query, "file_type": file_type},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to search files: {response.text}")
            return []
    except Exception as e:
        st.error(f"Error searching files: {str(e)}")
        return []

def generate_instagram_post(
    spreadsheet_id: str, 
    sheet_name: str,
    slides_template_id: str,
    drive_folder_id: str,
    recipient_email: str,
    access_token: str
) -> Dict[str, Any]:
    """Generate Instagram posts from spreadsheet data"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/instagram/generate",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name,
                "slides_template_id": slides_template_id,
                "drive_folder_id": drive_folder_id,
                "recipient_email": recipient_email
            }
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to generate posts: {response.text}")
            return {"success": False, "message": response.text}
    except Exception as e:
        st.error(f"Error generating posts: {str(e)}")
        return {"success": False, "message": str(e)}