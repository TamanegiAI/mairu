import streamlit as st
from datetime import datetime
import time
import json
from src.app.frontend.utils.api_helper import API_BASE_URL, search_drive_files, generate_instagram_post
import requests

def display_file_picker(file_type, access_token):
    """Display a file picker interface for Google Drive files"""
    st.write(f"Select your {file_type}")
    
    # Create a session state key for the selected file
    state_key = f"selected_{file_type.lower().replace(' ', '_')}"
    search_key = f"search_{file_type.lower().replace(' ', '_')}"
    
    # Initialize state for this file picker
    if state_key not in st.session_state:
        st.session_state[state_key] = None
    if search_key not in st.session_state:
        st.session_state[search_key] = ""
    
    # Search field
    search_query = st.text_input(f"Search {file_type}", key=search_key, 
                              placeholder=f"Type to search for {file_type}")
    
    # Only display when there's a search query
    if search_query:
        with st.spinner(f"Searching for {file_type}..."):
            try:
                # Make API call to backend to search for files
                headers = {"Authorization": f"Bearer {access_token}"}
                response = requests.get(
                    f"{API_BASE_URL}/drive/search", 
                    params={"query": search_query, "file_type": file_type.lower()},
                    headers=headers
                )
                
                if response.status_code == 200:
                    files = response.json()
                    
                    if not files:
                        st.info(f"No {file_type} files found matching '{search_query}'")
                    else:
                        # Display files in a radio button group
                        file_options = {f"{file['name']} ({file['id']})": file for file in files}
                        
                        selected_file = st.radio(
                            f"Select a {file_type} file:",
                            options=list(file_options.keys()),
                            key=f"radio_{file_type}"
                        )
                        
                        if selected_file:
                            st.session_state[state_key] = file_options[selected_file]
                else:
                    st.error(f"Error searching for {file_type}: {response.text}")
            except Exception as e:
                st.error(f"Error connecting to API: {str(e)}")
    
    # Display selected file info
    if st.session_state[state_key]:
        st.success(f"Selected {file_type}: {st.session_state[state_key]['name']}")
        return st.session_state[state_key]['id']
    return None

def get_sheet_columns(sheet_id, access_token):
    """Get column names from a spreadsheet"""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            f"{API_BASE_URL}/columns/{sheet_id}", 
            headers=headers
        )
        
        if response.status_code == 200:
            columns = response.json()
            return [col["name"] for col in columns]
        else:
            st.error(f"Error fetching sheet columns: {response.text}")
            return []
    except Exception as e:
        st.error(f"Error connecting to API: {str(e)}")
        return []

def analyze_slide_placeholders(slide_id, access_token):
    """Analyze a slide template for text placeholders"""
    # This would normally call an API to analyze the slide
    # For now, we'll use placeholder values
    return ["{{TEXT}}", "{{TITLE}}", "{{SUBTITLE}}"]

def display_image_automation():
    """Display the image automation UI"""
    st.header("Instagram Post Generation")
    
    # Check for access token
    access_token = st.session_state.get("access_token", None)
    if not access_token:
        st.warning("Authentication required. Please sign in first.")
        return
    
    # File picker section
    st.subheader("1. Select Files")
    
    # Create columns for better layout
    with st.container():
        # Spreadsheet selector
        spreadsheet_id = display_file_picker("Spreadsheet", access_token)
        
        # Slide template selector
        slides_template_id = display_file_picker("Slides Template", access_token)
        
        # Drive folder selector
        drive_folder_id = display_file_picker("Drive Folder", access_token)
    
    # Column mapping section
    st.subheader("2. Map Columns")
    
    # Initialize session state for column mappings if it doesn't exist
    if "column_mappings" not in st.session_state:
        st.session_state.column_mappings = {}
    
    # Only show mapping interface if spreadsheet and slides template are selected
    if spreadsheet_id and slides_template_id:
        # Get column names from the spreadsheet
        sheet_columns = get_sheet_columns(spreadsheet_id, access_token)
        
        # Get placeholder names from the slide template 
        # (in a real implementation, this would analyze the slide)
        placeholders = analyze_slide_placeholders(slides_template_id, access_token)
        
        if sheet_columns and placeholders:
            st.write("Map slide placeholders to spreadsheet columns:")
            
            # Display mapping fields for each placeholder
            for placeholder in placeholders:
                col_options = ["None"] + sheet_columns
                default_index = 0
                
                # Try to find appropriate default mapping based on common patterns
                if placeholder == "{{TEXT}}" or placeholder == "{{CONTENT}}":
                    for i, col in enumerate(col_options):
                        if "japanese" in col.lower() or "japanse" in col.lower() or "text" in col.lower():
                            default_index = i
                            break
                
                selected_col = st.selectbox(
                    f"Map {placeholder} to column:",
                    col_options,
                    index=default_index,
                    key=f"mapping_{placeholder}"
                )
                
                # Update the mapping in session state
                if selected_col != "None":
                    st.session_state.column_mappings[placeholder] = selected_col
                elif placeholder in st.session_state.column_mappings:
                    del st.session_state.column_mappings[placeholder]
        else:
            st.warning("Could not load columns or placeholders for mapping.")
    else:
        st.info("Please select both a spreadsheet and a slides template to set up column mapping.")
    
    # Conditional processing section
    st.subheader("3. Set Processing Conditions")
    
    with st.container():
        # Only enable if spreadsheet is selected
        if spreadsheet_id:
            sheet_columns = get_sheet_columns(spreadsheet_id, access_token)
            
            # Flag column selection
            flag_options = ["None (process all rows)"] + sheet_columns
            selected_flag_column = st.selectbox(
                "Process rows based on column value:",
                flag_options,
                key="process_flag_column"
            )
            
            # Flag value input
            flag_value = st.text_input(
                "Process rows where the selected column equals:",
                value="yes",
                disabled=(selected_flag_column == "None (process all rows)"),
                key="process_flag_value"
            )
            
            if selected_flag_column == "None (process all rows)":
                process_flag_column = None
            else:
                process_flag_column = selected_flag_column
        else:
            st.info("Please select a spreadsheet to set up processing conditions.")
            process_flag_column = None
            flag_value = "yes"
    
    # Configuration section  
    st.subheader("4. Configure")
    
    with st.form("instagram_post_form"):
        # Sheet name input
        sheet_name = st.text_input("Sheet Name", value="Sheet1", 
                                help="Name of the sheet containing your content")
        
        # Recipient email
        recipient_email = st.text_input("Recipient Email", 
                                     help="Email address to receive the generated posts")
        
        # Submit button
        generate_button = st.form_submit_button("Generate Instagram Posts")
        
        if generate_button:
            if not (spreadsheet_id and slides_template_id and drive_folder_id and recipient_email):
                st.error("Please select all required files and provide an email address")
            else:
                with st.spinner("Generating Instagram posts..."):
                    try:
                        # Prepare column mappings
                        mappings = st.session_state.column_mappings if hasattr(st.session_state, 'column_mappings') else {}
                        
                        # Get process flag settings
                        flag_column = process_flag_column if process_flag_column != "None (process all rows)" else None
                        
                        # API call to backend to generate posts
                        headers = {"Authorization": f"Bearer {access_token}"}
                        data = {
                            "spreadsheet_id": spreadsheet_id,
                            "sheet_name": sheet_name,
                            "slides_template_id": slides_template_id,
                            "drive_folder_id": drive_folder_id,
                            "recipient_email": recipient_email,
                            "column_mappings": mappings,
                            "process_flag_column": flag_column,
                            "process_flag_value": flag_value
                        }
                        
                        response = requests.post(
                            f"{API_BASE_URL}/instagram/generate",
                            json=data,
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success("Instagram posts generated and sent successfully!")
                            st.info(f"Generated {result.get('count', 0)} posts and emailed to {recipient_email}")
                        else:
                            st.error(f"Error generating posts: {response.text}")
                    except Exception as e:
                        st.error(f"Error connecting to API: {str(e)}")
    
    # Implementation details expander
    with st.expander("How it works"):
        st.markdown("""
        **Instagram Post Generation**
        
        This tool automatically generates Instagram posts from your spreadsheet data:
        
        1. **Set up your spreadsheet** with columns for Date, English Text, Japanese Text, etc.
        2. **Create a Slides template** with text placeholders like {{TEXT}}, {{TITLE}}
        3. **Map your columns** to specify which spreadsheet data goes where in the slide
        4. **Set conditions** to only process rows with specific values (e.g., "yes" in the "Flag" column)
        5. **Generate posts** and receive them via email
        
        The tool processes each row in your spreadsheet according to your mapping and conditions.
        """)
        
    # Example code expander
    with st.expander("View Apps Script Code Reference"):
        st.code("""
function createInstagramPost() {
  const spreadsheetId = "1erFKgTUoqKuV8XDlucyOWd17-gZ0LyuXtWRo8e5tE50"; // Your Google Sheet ID
  const sheetName = "Sheet1"; // Your sheet name
  const slidesTemplateId = "1iTbvUFuoEbPLZSqFIpK2NXMxoDByiBNQSR8iexB5Pdc"; // Your Slides template ID
  const driveFolderId = "1-CdkBA8yIuk9sxPqzJ2nHIKuci-lmCfG"; // Your Drive folder ID
  const gmailSubject = "Your Instagram Post";

  // Process each row in the spreadsheet and create Instagram posts
  // For rows with Japanese text, the script will:
  // 1. Open the slide template
  // 2. Replace {{TEXT}} with Japanese text
  // 3. Replace the placeholder image
  // 4. Export as PNG
  // 5. Email the image
}
        """, language="javascript")