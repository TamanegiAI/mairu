# frontend/components/sheets.py
import streamlit as st
from src.app.frontend.utils.api_helper import get_sheets, get_sheet_columns, save_mapping

def load_sheets():
    """Load Google Sheets"""
    if not st.session_state.is_authenticated:
        st.warning("Please authenticate first.")
        return False
    
    with st.spinner("Loading sheets..."):
        sheets = get_sheets(st.session_state.access_token)
        if isinstance(sheets, list):
            st.session_state.sheets = sheets
            return True
        else:
            st.error(f"Failed to load sheets: {sheets.get('error') if isinstance(sheets, dict) else 'Unknown error'}")
            return False

def load_columns(sheet_id):
    """Load columns from the selected sheet"""
    if not sheet_id:
        st.warning("Please select a sheet first.")
        return False
    
    with st.spinner("Loading columns..."):
        columns = get_sheet_columns(sheet_id, st.session_state.access_token)
        if isinstance(columns, list):
            st.session_state.columns = columns
            return True
        else:
            st.error(f"Failed to load columns: {columns.get('error') if isinstance(columns, dict) else 'Unknown error'}")
            return False

def display_sheet_selection():
    """Display sheet selection UI"""
    st.header("Select Google Sheet")
    
    if not st.session_state.sheets:
        if st.button("Load Sheets"):
            load_sheets()
    
    if st.session_state.sheets:
        sheet_options = {sheet["name"]: sheet["id"] for sheet in st.session_state.sheets}
        selected_sheet_name = st.selectbox(
            "Select a Google Sheet", 
            options=list(sheet_options.keys())
        )
        
        if selected_sheet_name:
            st.session_state.selected_sheet_id = sheet_options[selected_sheet_name]
            st.session_state.selected_sheet_name = selected_sheet_name
            st.success(f"Selected sheet: {selected_sheet_name}")
        
        if st.button("Refresh Sheets"):
            load_sheets()

def display_template_selection():
    """Display template selection UI"""
    st.header("Select Document Template")
    template_id = st.text_input(
        "Enter Google Doc Template ID",
        help="Find the ID in the URL: docs.google.com/document/d/[ID]/edit"
    )
    if template_id:
        st.session_state.template_id = template_id
        st.session_state.selected_template_id = template_id
        st.success("Template ID saved")

def display_mapping_ui():
    """Display column mapping UI"""
    st.header("Map Columns to Placeholders")
    
    if hasattr(st.session_state, 'selected_sheet_id'):
        if not st.session_state.columns:
            if st.button("Load Columns"):
                load_columns(st.session_state.selected_sheet_id)
        
        if st.session_state.columns:
            st.write("Map sheet columns to document placeholders:")
            
            # Create a form for mapping columns to placeholders
            mappings = {}
            for column in st.session_state.columns:
                placeholder = st.text_input(
                    f"Placeholder for '{column['name']}'",
                    key=f"placeholder_{column['index']}",
                    placeholder="e.g., Name"
                )
                if placeholder:
                    mappings[placeholder] = column["name"]
            
            st.session_state.mappings = mappings
            st.session_state.column_mappings = mappings  # For compatibility with updated component
            
            if st.button("Save Mappings"):
                if not mappings:
                    st.warning("Please create at least one mapping")
                else:
                    result = save_mapping(
                        st.session_state.selected_sheet_id, 
                        st.session_state.template_id,
                        mappings,
                        st.session_state.access_token
                    )
                    if result.get("success", False):
                        st.success("Mappings saved successfully!")
            
            if st.button("Refresh Columns"):
                load_columns(st.session_state.selected_sheet_id)
    else:
        st.warning("Please select a sheet first (in Step 1)")