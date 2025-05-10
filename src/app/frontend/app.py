import streamlit as st
from datetime import datetime
import time

# Import components
from src.app.frontend.components.auth import authenticate, logout, display_auth_status
from src.app.frontend.components.sheets import display_sheet_selection, display_template_selection, display_mapping_ui
from src.app.frontend.components.document_generation import display_generation_tab
from src.app.frontend.components.email_scheduling import display_email_config, display_send_schedule

# Configure the page
st.set_page_config(
    page_title="Google Docs Automation",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# State management
if 'is_authenticated' not in st.session_state:
    st.session_state.is_authenticated = False
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'sheets' not in st.session_state:
    st.session_state.sheets = []
if 'columns' not in st.session_state:
    st.session_state.columns = []
if 'generated_doc_id' not in st.session_state:
    st.session_state.generated_doc_id = None

# Main app UI
def main():
    st.title("Google Docs Automation 🚀")
    
    # Authentication section
    display_auth_status()
    
    # Main content
    if st.session_state.is_authenticated:
        # Create tabs for the workflow
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "1. Select Sheet", 
            "2. Select Template",
            "3. Map Columns",
            "4. Email Config",
            "5. Send or Schedule"
        ])
        
        # Tab 1: Select Google Sheet
        with tab1:
            display_sheet_selection()
        
        # Tab 2: Select Template
        with tab2:
            display_template_selection()
        
        # Tab 3: Map Columns
        with tab3:
            display_mapping_ui()
        
        # Tab 4: Email Configuration
        with tab4:
            display_email_config()
        
        # Tab 5: Send or Schedule
        with tab5:
            display_send_schedule()
    else:
        st.info("Please sign in with Google to use the application.")
        authenticate()

if __name__ == "__main__":
    main()