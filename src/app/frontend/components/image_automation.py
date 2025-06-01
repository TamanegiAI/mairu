import streamlit as st
from datetime import datetime
import time
import json
from src.app.frontend.utils.api_helper import API_BASE_URL, search_drive_files, generate_instagram_post, configure_folder_monitoring, get_folder_monitoring_status
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

    # Initialize session state for folder monitoring if not already present
    if 'monitoring_trigger_folder_id' not in st.session_state:
        st.session_state.monitoring_trigger_folder_id = None
    if 'monitoring_trigger_folder_name' not in st.session_state:
        st.session_state.monitoring_trigger_folder_name = ""
    if 'monitoring_backup_folder_id' not in st.session_state:
        st.session_state.monitoring_backup_folder_id = None
    if 'monitoring_backup_folder_name' not in st.session_state:
        st.session_state.monitoring_backup_folder_name = ""
    if 'monitoring_enabled' not in st.session_state:
        st.session_state.monitoring_enabled = False
    if 'monitoring_frequency' not in st.session_state:
        st.session_state.monitoring_frequency = 15 # Default to 15 minutes
    if 'monitoring_status_column' not in st.session_state:
        st.session_state.monitoring_status_column = ""
    if 'monitoring_active_status' not in st.session_state:
        st.session_state.monitoring_active_status = "Unknown"
    if 'monitoring_last_processed_image' not in st.session_state:
        st.session_state.monitoring_last_processed_image = "N/A"
    if 'monitoring_last_check_time' not in st.session_state:
        st.session_state.monitoring_last_check_time = "N/A"
    if 'monitoring_error_message' not in st.session_state:
        st.session_state.monitoring_error_message = ""
    if 'monitoring_status_sheet_columns' not in st.session_state:
        st.session_state.monitoring_status_sheet_columns = []
    if 'folder_workflow_status_loaded' not in st.session_state:
        st.session_state.folder_workflow_status_loaded = False
    
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
    
    # --- Folder Workflow Callbacks ---
    def update_monitoring_status_display():
        if st.session_state.get("access_token"):
            status_data = get_folder_monitoring_status(st.session_state.access_token)
            if status_data:
                st.session_state.monitoring_active_status = "Active" if status_data.get('is_monitoring_active') else "Inactive"
                st.session_state.monitoring_last_processed_image = status_data.get('last_processed_image_name', 'N/A')
                st.session_state.monitoring_last_check_time = status_data.get('last_check_time', 'N/A')
                st.session_state.monitoring_error_message = status_data.get('error_message', '')
                
                current_config = status_data.get('current_config')
                if current_config: # Pre-fill config from status if available
                    st.session_state.monitoring_enabled = current_config.get('monitoring_enabled', st.session_state.monitoring_enabled)
                    st.session_state.monitoring_frequency = current_config.get('monitoring_frequency_minutes', st.session_state.monitoring_frequency)
                    st.session_state.monitoring_status_column = current_config.get('status_column_name', st.session_state.monitoring_status_column)
                    # We could also pre-fill folder names/IDs if we store them more robustly from display_file_picker
            else:
                st.session_state.monitoring_active_status = "Error fetching status"
                st.session_state.monitoring_error_message = "Failed to connect to backend or parse status."
        st.session_state.folder_workflow_status_loaded = True # Mark as loaded

    def handle_save_monitoring_config():
        if not st.session_state.get("access_token"):
            st.error("Authentication token not found. Please re-authenticate.")
            return

        if not st.session_state.monitoring_trigger_folder_id or not st.session_state.monitoring_backup_folder_id:
            st.error("Please select both Trigger and Backup folders.")
            return
        
        # spreadsheet_id should be available from section 1
        current_spreadsheet_id = None
        if st.session_state.get('selected_spreadsheet') and st.session_state.selected_spreadsheet.get('id'):
            current_spreadsheet_id = st.session_state.selected_spreadsheet.get('id')
        elif spreadsheet_id: # Fallback to the variable if display_file_picker sets it directly
             current_spreadsheet_id = spreadsheet_id

        if not current_spreadsheet_id:
            st.error("Spreadsheet ID not found. Please select a spreadsheet in Section 1.")
            return

        if st.session_state.monitoring_enabled and not st.session_state.monitoring_status_column:
            st.warning("It's recommended to select a Status Column when monitoring is enabled.")

        config_data = {
            "trigger_folder_id": st.session_state.monitoring_trigger_folder_id,
            "backup_folder_id": st.session_state.monitoring_backup_folder_id,
            "monitoring_enabled": st.session_state.monitoring_enabled,
            "monitoring_frequency_minutes": st.session_state.monitoring_frequency,
            "status_column_name": st.session_state.monitoring_status_column,
            "spreadsheet_id": current_spreadsheet_id
        }
        
        response = configure_folder_monitoring(config_data, st.session_state.access_token)
        if response and response.get("success"):
            st.success(response.get("message", "Monitoring configuration saved successfully!"))
            update_monitoring_status_display() # Refresh status after saving
        else:
            error_msg = response.get("message", "Failed to save monitoring configuration.")
            detail = response.get("error_detail", response.get("detail")) # Check for 'detail' too
            if detail and isinstance(detail, str): error_msg += f" Details: {detail}"
            elif detail: error_msg += f" Details: {json.dumps(detail)}"
            st.error(error_msg)

    # Section 5: Folder Workflow
    st.subheader("5. Folder Workflow")
    if not st.session_state.folder_workflow_status_loaded and access_token:
        update_monitoring_status_display() # Initial load of status
    
    with st.container():
        st.markdown("#### 1. Folder Selection")

        # Image Trigger Folder selector
        selected_trigger_folder_id = display_file_picker("Image Trigger Folder", access_token)
        if selected_trigger_folder_id:
            st.session_state.monitoring_trigger_folder_id = selected_trigger_folder_id
            trigger_folder_details_key = "selected_image_trigger_folder" # Key used by display_file_picker
            folder_details = st.session_state.get(trigger_folder_details_key)
            if folder_details and folder_details.get('id') == selected_trigger_folder_id:
                st.session_state.monitoring_trigger_folder_name = folder_details.get('name', selected_trigger_folder_id)
            else:
                st.session_state.monitoring_trigger_folder_name = selected_trigger_folder_id # Fallback to ID
        elif st.session_state.monitoring_trigger_folder_id: # If already set, display its name
            st.text(f"Selected Trigger Folder: {st.session_state.get('monitoring_trigger_folder_name', st.session_state.monitoring_trigger_folder_id)}")

        # Image Backup/Done Folder selector
        selected_backup_folder_id = display_file_picker("Image Backup/Done Folder", access_token)
        if selected_backup_folder_id:
            st.session_state.monitoring_backup_folder_id = selected_backup_folder_id
            backup_folder_details_key = "selected_image_backup_done_folder" # Key used by display_file_picker
            folder_details = st.session_state.get(backup_folder_details_key)
            if folder_details and folder_details.get('id') == selected_backup_folder_id:
                st.session_state.monitoring_backup_folder_name = folder_details.get('name', selected_backup_folder_id)
            else:
                st.session_state.monitoring_backup_folder_name = selected_backup_folder_id # Fallback to ID
        elif st.session_state.monitoring_backup_folder_id: # If already set, display its name
            st.text(f"Selected Backup Folder: {st.session_state.get('monitoring_backup_folder_name', st.session_state.monitoring_backup_folder_id)}")

        st.markdown("---") # Visual separator
        st.markdown("#### 2. Monitoring Configuration")

        st.markdown("**Monitoring Configuration**")
        st.session_state.monitoring_enabled = st.toggle("Enable Automatic Monitoring", value=st.session_state.monitoring_enabled, key='monitoring_toggle')
        st.session_state.monitoring_frequency = st.number_input("Monitoring Frequency (minutes)", min_value=1, value=st.session_state.monitoring_frequency, key='monitoring_freq_input')
        
        if spreadsheet_id: # Ensure spreadsheet_id is selected from section 1
            # Populate sheet_columns for status dropdown if not already populated or if spreadsheet_id changed
            if not st.session_state.monitoring_status_sheet_columns or st.session_state.get('current_spreadsheet_id_for_status_col') != spreadsheet_id:
                st.session_state.monitoring_status_sheet_columns = get_sheet_columns(spreadsheet_id, access_token)
                st.session_state.current_spreadsheet_id_for_status_col = spreadsheet_id

            status_column_options = ["None"] + st.session_state.monitoring_status_sheet_columns
            
            # Try to find current index for selected_status_column
            current_status_col_index = 0
            if st.session_state.monitoring_status_column and st.session_state.monitoring_status_column in status_column_options:
                current_status_col_index = status_column_options.index(st.session_state.monitoring_status_column)

            selected_status_col_from_ui = st.selectbox(
                "Status Column (in Spreadsheet from section 1 to update)",
                status_column_options,
                index=current_status_col_index,
                key="monitoring_status_column_selector"
            )
            st.session_state.monitoring_status_column = selected_status_col_from_ui if selected_status_col_from_ui != "None" else ""
        else:
            st.info("Select a Spreadsheet in section 1 to choose a Status Column for monitoring.")
        
        st.button("Save Monitoring Configuration", on_click=handle_save_monitoring_config, key='save_monitoring_config_button')
        # Corrected indentation for the following lines
        # This 'else' block for spreadsheet_id check was problematic, removing it as the st.info above covers it.
        # else:
        #     st.info("Select a spreadsheet in '1. Select Files' to choose a status column for monitoring.")
        #     # Reset status column if spreadsheet is not selected
        #     st.session_state.monitoring_status_column = "" # Use the correct session state var

        st.markdown("---") # Visual separator
        st.markdown("#### 3. Status Information")

        # Initialize session states for status info if they don't exist
        if 'monitoring_status_display' not in st.session_state:
            st.session_state.monitoring_status_display = "Monitoring: Inactive"
        if 'last_processed_image_info' not in st.session_state:
            st.session_state.last_processed_image_info = "Last Processed: N/A"

        # Display current monitoring status
        st.button("Refresh Monitoring Status", on_click=update_monitoring_status_display, key='refresh_monitoring_status_button')
        st.text(f"Current Monitoring Status: {st.session_state.monitoring_active_status}")
        st.text(f"Last Processed Image: {st.session_state.monitoring_last_processed_image}")
        st.text(f"Last Checked: {st.session_state.monitoring_last_check_time}")
        if st.session_state.monitoring_error_message:
            st.error(f"Last Error: {st.session_state.monitoring_error_message}")
        
        # Placeholder for a button to manually trigger a check, if desired in future
        # if st.button("Check Trigger Folder Now"):
        #    st.info("Manual check triggered (feature to be implemented).")

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