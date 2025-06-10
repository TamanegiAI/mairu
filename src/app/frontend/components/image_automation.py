import streamlit as st
from datetime import datetime
import time
import json
from src.app.frontend.utils.api_helper import API_BASE_URL, search_drive_files, generate_instagram_post, configure_folder_monitoring, get_folder_monitoring_status

# Helper functions for monitoring configuration UI
def update_monitoring_dropdown_options(spreadsheet_id_to_use, access_token_to_use):
    # Ensure dependent session state variables for dropdowns exist, even if empty initially
    if 'monitoring_status_sheet_columns' not in st.session_state:
        st.session_state.monitoring_status_sheet_columns = ["None (do not update status)"]
    if 'monitoring_pfc_options' not in st.session_state:
        st.session_state.monitoring_pfc_options = ["None (process all rows)"]
    
    # Note: Don't set monitoring_status_column and monitoring_process_flag_column here
    # since they are controlled by widgets with keys

    if spreadsheet_id_to_use and access_token_to_use:
        cols = get_sheet_columns(spreadsheet_id_to_use, access_token_to_use)
        common_cols = cols if cols else []

        st.session_state.monitoring_status_sheet_columns = ["None (do not update status)"] + common_cols
        st.session_state.monitoring_pfc_options = ["None (process all rows)"] + common_cols
        st.session_state._monitoring_pfc_options_source_id = spreadsheet_id_to_use

        # Note: Widget-controlled values (monitoring_status_column, monitoring_process_flag_column) 
        # are managed by their respective widgets, not set programmatically
            
    else: 
        st.session_state.monitoring_status_sheet_columns = ["None (do not update status)"]
        st.session_state.monitoring_pfc_options = ["None (process all rows)"]
        # Note: Don't set widget-controlled values here
        if '_monitoring_pfc_options_source_id' in st.session_state: # Clear source tracker
            del st.session_state['_monitoring_pfc_options_source_id']

def handle_monitoring_spreadsheet_id_change():
    access_token = st.session_state.get("access_token")
    # The text_input for monitoring_spreadsheet_id directly updates st.session_state.monitoring_spreadsheet_id
    spreadsheet_id = st.session_state.get("monitoring_spreadsheet_id") 
    update_monitoring_dropdown_options(spreadsheet_id, access_token)

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

    # Initialize session state for shared fields
    if 'shared_recipient_email' not in st.session_state:
        st.session_state.shared_recipient_email = ""
    if 'shared_sheet_name' not in st.session_state:
        st.session_state.shared_sheet_name = "Sheet1"

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

    # === SHARED CONFIGURATION SECTION ===
    st.subheader("📧 Shared Configuration")
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            st.text_input(
                "Recipient Email", 
                value=st.session_state.shared_recipient_email,
                key='shared_recipient_email',
                help="Email address to receive generated Instagram posts"
            )
        
        with col2:
            st.text_input(
                "Sheet Name", 
                value=st.session_state.shared_sheet_name,
                key='shared_sheet_name',
                help="Name of the sheet tab in your spreadsheet (e.g., 'Sheet1')"
            )

    # Section 1: File Selection (keep as is)
    st.subheader("1. File Selection")
    
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
    
    # The manual configuration section has been moved to the end of the function.
    
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
                if current_config:
                    # Fields primarily from backend config, with some fallback considerations
                    st.session_state.monitoring_enabled = current_config.get('enabled', st.session_state.get('monitoring_enabled', False))
                    st.session_state.monitoring_trigger_folder_id = current_config.get('trigger_folder_id', st.session_state.get('monitoring_trigger_folder_id'))
                    st.session_state.monitoring_backup_folder_id = current_config.get('backup_folder_id', st.session_state.get('monitoring_backup_folder_id'))
                    # Note: monitoring_frequency is controlled by widget, don't set programmatically
                    
                    # Spreadsheet ID: Config -> General Session -> Default Empty
                    st.session_state.monitoring_spreadsheet_id = current_config.get('spreadsheet_id')
                    if not st.session_state.monitoring_spreadsheet_id and st.session_state.get('selected_spreadsheet'):
                        st.session_state.monitoring_spreadsheet_id = st.session_state.selected_spreadsheet.get('id')
                    if not st.session_state.monitoring_spreadsheet_id: # Ultimate fallback
                         st.session_state.monitoring_spreadsheet_id = ""

                    # Sheet Name: Config -> Default 'Sheet1'
                    st.session_state.monitoring_sheet_name = current_config.get('sheet_name')
                    if st.session_state.monitoring_sheet_name is None: # Check for None specifically if not in config
                        st.session_state.monitoring_sheet_name = "Sheet1"

                    # Slides Template ID: Config -> General Session -> Default Empty
                    st.session_state.monitoring_slides_template_id = current_config.get('slides_template_id')
                    if not st.session_state.monitoring_slides_template_id and st.session_state.get('selected_slides_template'):
                        st.session_state.monitoring_slides_template_id = st.session_state.selected_slides_template.get('id')
                    if not st.session_state.monitoring_slides_template_id:
                        st.session_state.monitoring_slides_template_id = ""

                    # Recipient Email: Config -> Default Empty
                    st.session_state.monitoring_recipient_email = current_config.get('recipient_email')
                    if not st.session_state.monitoring_recipient_email:
                         st.session_state.monitoring_recipient_email = ""

                    # Column Mappings: Config -> General Session -> Default Empty JSON
                    column_mappings_from_config = current_config.get('column_mappings')
                    if column_mappings_from_config is not None:
                        try:
                            st.session_state.monitoring_column_mappings_json = json.dumps(column_mappings_from_config, indent=2) if column_mappings_from_config else "{}"
                        except TypeError:
                            st.session_state.monitoring_column_mappings_json = "{}"
                    elif st.session_state.get('column_mappings'):
                        try:
                            st.session_state.monitoring_column_mappings_json = json.dumps(st.session_state.column_mappings, indent=2) if st.session_state.column_mappings else "{}"
                        except TypeError:
                            st.session_state.monitoring_column_mappings_json = "{}"
                    else:
                        st.session_state.monitoring_column_mappings_json = "{}"

                    # Note: monitoring_process_flag_column, monitoring_process_flag_value, 
                    # and monitoring_status_column are controlled by widgets, don't set programmatically

                else: # No current_config from backend, so populate from general session state or defaults
                    st.session_state.monitoring_enabled = st.session_state.get('monitoring_enabled', False)
                    st.session_state.monitoring_trigger_folder_id = st.session_state.get('monitoring_trigger_folder_id') # Retain if already set, else None
                    st.session_state.monitoring_backup_folder_id = st.session_state.get('monitoring_backup_folder_id') # Retain if already set, else None
                    # Note: monitoring_frequency is controlled by widget, don't set programmatically

                    if st.session_state.get('selected_spreadsheet'):
                        st.session_state.monitoring_spreadsheet_id = st.session_state.selected_spreadsheet.get('id', "")
                    else:
                        st.session_state.monitoring_spreadsheet_id = ""
                    
                    st.session_state.monitoring_sheet_name = "Sheet1" # Default

                    if st.session_state.get('selected_slides_template'):
                        st.session_state.monitoring_slides_template_id = st.session_state.selected_slides_template.get('id', "")
                    else:
                        st.session_state.monitoring_slides_template_id = ""

                    st.session_state.monitoring_recipient_email = "" # Default

                    if st.session_state.get('column_mappings'):
                        try:
                            st.session_state.monitoring_column_mappings_json = json.dumps(st.session_state.column_mappings, indent=2) if st.session_state.column_mappings else "{}"
                        except TypeError:
                            st.session_state.monitoring_column_mappings_json = "{}"
                    else:
                        st.session_state.monitoring_column_mappings_json = "{}"

                    # Note: monitoring_process_flag_column, monitoring_process_flag_value, 
                    # and monitoring_status_column are controlled by widgets, don't set programmatically

                # Common logic: Update dropdowns based on the determined spreadsheet ID
                update_monitoring_dropdown_options(st.session_state.monitoring_spreadsheet_id, st.session_state.get("access_token"))
            
            else: # Corresponds to 'if status_data:' - problem fetching status
                st.session_state.monitoring_active_status = "Error fetching status"
                st.session_state.monitoring_error_message = "Failed to connect to backend or parse status."
                # Attempt to pre-fill from general session state even if status fetch fails, for a better UX on first load
                if not st.session_state.folder_workflow_status_loaded: # Only on first attempt if status fails
                    if st.session_state.get('selected_spreadsheet'):
                        st.session_state.monitoring_spreadsheet_id = st.session_state.selected_spreadsheet.get('id', "")
                    else:
                        st.session_state.monitoring_spreadsheet_id = ""
                    st.session_state.monitoring_sheet_name = "Sheet1"
                    if st.session_state.get('selected_slides_template'):
                        st.session_state.monitoring_slides_template_id = st.session_state.selected_slides_template.get('id', "")
                    else:
                        st.session_state.monitoring_slides_template_id = ""
                    st.session_state.monitoring_recipient_email = ""
                    if st.session_state.get('column_mappings'):
                        try: st.session_state.monitoring_column_mappings_json = json.dumps(st.session_state.column_mappings, indent=2)
                        except TypeError: st.session_state.monitoring_column_mappings_json = "{}"
                    else: st.session_state.monitoring_column_mappings_json = "{}"
                    # Note: monitoring widgets are controlled by their respective widgets
                    update_monitoring_dropdown_options(st.session_state.monitoring_spreadsheet_id, st.session_state.get("access_token"))

        st.session_state.folder_workflow_status_loaded = True # Mark as loaded

    def handle_save_monitoring_config():
        if not st.session_state.get("access_token"):
            st.error("Authentication token not found. Please re-authenticate.")
            return

        if not st.session_state.monitoring_trigger_folder_id or not st.session_state.monitoring_backup_folder_id:
            st.error("Please select both Trigger and Backup folders.")
            return
        
        if not st.session_state.shared_recipient_email or not st.session_state.shared_sheet_name:
            st.error("Please fill in the recipient email and sheet name in the shared configuration section.")
            return
        
        # Get spreadsheet and slides template IDs from session state
        selected_spreadsheet_id = st.session_state.get('selected_spreadsheet', {}).get('id', '')
        selected_slides_template_id = st.session_state.get('selected_slides_template', {}).get('id', '')
        
        if not selected_spreadsheet_id:
            st.error("Please select a spreadsheet in the File Selection section.")
            return
            
        if not selected_slides_template_id:
            st.error("Please select a slides template in the File Selection section.")
            return

        if st.session_state.monitoring_enabled and not st.session_state.monitoring_status_column:
            st.warning("It's recommended to select a Status Column when monitoring is enabled.")

        # Use column mappings from the main section, or default to empty
        column_mappings_dict = st.session_state.get('column_mappings', {})
        
        config_data = {
            "enabled": st.session_state.monitoring_enabled,
            "trigger_folder_id": st.session_state.monitoring_trigger_folder_id,
            "backup_folder_id": st.session_state.monitoring_backup_folder_id,
            # Use the selected spreadsheet from section 1
            "spreadsheet_id": selected_spreadsheet_id,
            "status_column_name": st.session_state.monitoring_status_column if st.session_state.monitoring_status_column != "None (do not update status)" else None,
            "monitoring_frequency_minutes": st.session_state.monitoring_frequency,
            
            # Use shared configuration
            "sheet_name": st.session_state.shared_sheet_name,
            "slides_template_id": selected_slides_template_id,
            "recipient_email": st.session_state.shared_recipient_email,
            "column_mappings": column_mappings_dict,
            "process_flag_column": st.session_state.get('monitoring_process_flag_column') if st.session_state.get('monitoring_process_flag_column') != "None (process all rows)" else st.session_state.get('process_flag_column'),
            "process_flag_value": st.session_state.get('monitoring_process_flag_value', st.session_state.get('process_flag_value', 'yes')),
            "background_image_id": st.session_state.get('background_image_id'),
            "backup_folder_id": st.session_state.get('monitoring_backup_folder_id')
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
    # Section 5: Folder Workflow / Image Trigger Automation
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
        elif st.session_state.get('monitoring_trigger_folder_id'): # If already set, display its name
            st.text(f"Selected Trigger Folder: {st.session_state.get('monitoring_trigger_folder_name', st.session_state.monitoring_trigger_folder_id)}")
        
        # Image Backup Folder selector
        selected_backup_folder_id = display_file_picker("Image Backup Folder", access_token)
        if selected_backup_folder_id:
            st.session_state.monitoring_backup_folder_id = selected_backup_folder_id
            backup_folder_details_key = "selected_image_backup_folder" # Key used by display_file_picker
            folder_details = st.session_state.get(backup_folder_details_key)
            if folder_details and folder_details.get('id') == selected_backup_folder_id:
                st.session_state.monitoring_backup_folder_name = folder_details.get('name', selected_backup_folder_id)
            else:
                st.session_state.monitoring_backup_folder_name = selected_backup_folder_id # Fallback to ID
        elif st.session_state.get('monitoring_backup_folder_id'): # If already set, display its name
            st.text(f"Selected Backup Folder: {st.session_state.get('monitoring_backup_folder_name', st.session_state.monitoring_backup_folder_id)}")

    st.markdown("#### 2. Monitoring Configuration")
    
    # Check if required fields are filled
    can_start_monitoring = (
        st.session_state.shared_recipient_email and 
        st.session_state.shared_sheet_name and
        st.session_state.monitoring_trigger_folder_id and 
        st.session_state.monitoring_backup_folder_id
    )
    
    if not can_start_monitoring:
        st.warning("⚠️ Please complete the following before starting monitoring:")
        if not st.session_state.shared_recipient_email:
            st.write("- Fill in the recipient email in the shared configuration")
        if not st.session_state.shared_sheet_name:
            st.write("- Fill in the sheet name in the shared configuration")
        if not st.session_state.monitoring_trigger_folder_id:
            st.write("- Select an Image Trigger Folder")
        if not st.session_state.monitoring_backup_folder_id:
            st.write("- Select an Image Backup Folder")
    else:
        st.success(f"✅ Ready to monitor | Email: '{st.session_state.shared_recipient_email}' | Sheet: '{st.session_state.shared_sheet_name}'")

    st.number_input(
        "Monitoring Frequency (minutes)", 
        min_value=1, 
        value=st.session_state.get('monitoring_frequency', 15), 
        key='monitoring_frequency'
    )

    # Pre-calculate index for Process Flag Column selectbox
    pfc_options = st.session_state.get('monitoring_pfc_options', ["None (process all rows)"])
    pfc_current_value = st.session_state.get('monitoring_process_flag_column', "None (process all rows)")
    pfc_index = 0
    try:
        if pfc_current_value in pfc_options:
            pfc_index = pfc_options.index(pfc_current_value)
        elif pfc_options: # If current value not in options, default to first option if available
            pfc_index = 0 
            st.session_state.monitoring_process_flag_column = pfc_options[0]
    except ValueError: # Should not happen if pfc_options is a list
        pfc_index = 0
    
    st.selectbox(
        "Process Flag Column (Optional)",
        options=pfc_options,
        index=pfc_index,
        key='monitoring_process_flag_column', # Corrected key
        help='Select a column to check for a specific value before processing a row. If \'None\', all rows are candidates.'
    )

    st.text_input(
        "Process Flag Value",
        value=st.session_state.get('monitoring_process_flag_value', 'yes'),
        key='monitoring_process_flag_value', # Corrected key
        help="The value to look for in the 'Process Flag Column'. Processing occurs if the column value matches this."
    )

    # Pre-calculate index for Status Column Name selectbox
    status_options = st.session_state.get('monitoring_status_sheet_columns', ["None (do not update status)"])
    status_current_value = st.session_state.get('monitoring_status_column', "None (do not update status)")
    status_index = 0
    try:
        if status_current_value in status_options:
            status_index = status_options.index(status_current_value)
        elif status_options: # If current value not in options, default to first option if available
            status_index = 0
            st.session_state.monitoring_status_column = status_options[0]
    except ValueError:
        status_index = 0

    st.selectbox(
        "Status Column Name (Optional)",
        options=status_options,
        index=status_index,
        key='monitoring_status_column',
        help="Select a column to store processing status like 'Sent', 'Failed', etc. If 'None', no status updates."
    )

    # Start/Stop Monitoring buttons
    st.markdown("#### Start/Stop Monitoring")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Start Monitoring", disabled=not can_start_monitoring, type="primary"):
            st.session_state.monitoring_enabled = True
            handle_save_monitoring_config()
    
    with col2:
        if st.button("⏹️ Stop Monitoring", disabled=not st.session_state.get('monitoring_enabled', False)):
            st.session_state.monitoring_enabled = False
            handle_save_monitoring_config()
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

    # Configuration section for Manual Instagram Post Generation (moved to end)
    st.markdown("---") # Add a separator
    st.subheader("Manual Instagram Post Generation")
    
    # Use shared configuration
    manual_sheet_name = st.session_state.shared_sheet_name
    manual_recipient_email = st.session_state.shared_recipient_email
    
    if not manual_recipient_email or not manual_sheet_name:
        st.warning("⚠️ Please fill in the shared email and sheet name in the configuration section above.")
    else:
        st.success(f"✅ Using: Sheet '{manual_sheet_name}' | Email: '{manual_recipient_email}'")
    
    # Image selection
    st.subheader("Select Background Image")
    if 'background_image_id' not in st.session_state:
        st.session_state.background_image_id = None
    
    # Display file picker and update session state when an image is selected
    selected_image = display_file_picker("Background Image", access_token)
    if selected_image:
        st.session_state.background_image_id = selected_image
    
    # Show selected image ID if any
    if st.session_state.background_image_id:
        st.info(f"Selected Image ID: {st.session_state.background_image_id}")
    
    # Submit button
    manual_generate_button = st.button("Generate Instagram Posts (Manual)", key="manual_generate_button")
    
    if manual_generate_button:
        if not spreadsheet_id or not slides_template_id or not drive_folder_id:
            st.error("Please select all required files (Spreadsheet, Slides Template, and Drive Folder)")
        else:
            with st.spinner("Generating Instagram posts..."):
                result = generate_instagram_post(
                    spreadsheet_id=spreadsheet_id,
                    sheet_name=manual_sheet_name,
                    slides_template_id=slides_template_id,
                    drive_folder_id=drive_folder_id,
                    recipient_email=manual_recipient_email,
                    access_token=access_token,
                    background_image_id=st.session_state.background_image_id,
                    column_mappings=st.session_state.column_mappings if hasattr(st.session_state, 'column_mappings') else None,
                    process_flag_column=st.session_state.process_flag_column if hasattr(st.session_state, 'process_flag_column') else None,
                    process_flag_value=st.session_state.process_flag_value if hasattr(st.session_state, 'process_flag_value') else "yes"
                )
                
                if result.get("success"):
                    st.success(f"Successfully generated {result.get('count', 0)} posts!")
                    if result.get("files"):
                        st.write("Generated files:")
                        for file in result["files"]:
                            st.write(f"- {file['name']} (ID: {file['png_id']})")
                else:
                    st.error(f"Failed to generate posts: {result.get('message', 'Unknown error')}")