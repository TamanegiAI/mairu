import streamlit as st
from datetime import datetime
import time

# Import components
from src.app.frontend.components.auth import authenticate, logout, display_auth_status
from src.app.frontend.components.sheets import display_sheet_selection, display_template_selection, display_mapping_ui
from src.app.frontend.components.document_generation import display_generation_tab
from src.app.frontend.components.email_scheduling import display_email_config, display_send_schedule

# Try importing the image automation component if it exists
try:
    from src.app.frontend.components.image_automation import display_image_automation
except ImportError:
    display_image_automation = None

# Configure the page
st.set_page_config(
    page_title="Marketting Automation",
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
if 'current_section' not in st.session_state:
    st.session_state.current_section = "mail"

def show_mail_automation():
    st.session_state.current_section = "mail"
    
def show_image_automation():
    st.session_state.current_section = "image"

# Main app UI
def main():
    st.title("Google Docs Automation 🚀")
    
    # Authentication section
    display_auth_status()
    
    # Sidebar navigation
    with st.sidebar:
        st.title("Marketing Automation")
        st.button("Image Automation", on_click=show_image_automation,
                 use_container_width=True,
                 type="primary" if st.session_state.current_section == "image" else "secondary")
        st.button("Mail Automation", on_click=show_mail_automation, 
                 use_container_width=True,
                 type="primary" if st.session_state.current_section == "mail" else "secondary")

        
        st.divider()
        st.caption("© 2025 Google Docs Automation")
    
    # Main content
    if st.session_state.is_authenticated:
        if st.session_state.current_section == "mail":
            st.header("Mail Automation")
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
        
        elif st.session_state.current_section == "image":
            st.header("Image Automation")
            
            if display_image_automation:
                display_image_automation()
            else:
                st.warning("Image Automation component is not available. Please check your installation.")
                
                # Display placeholder UI until the component is implemented
                st.subheader("Instagram Post Generator")
                
                with st.form("instagram_placeholder_form"):
                    st.text_input("Spreadsheet ID", help="The ID of your Google Sheet with content")
                    st.text_input("Slides Template ID", help="The ID of your Google Slides template")
                    st.text_input("Drive Folder ID", help="The ID of the folder to save images")
                    st.text_input("Recipient Email", help="Email to receive generated posts")
                    st.form_submit_button("Generate Posts", disabled=True)
                
                with st.expander("How it works"):
                    st.info("This feature is coming soon! It will allow you to automatically generate Instagram posts from your Google Sheets data using Google Slides templates.")
    else:
        st.info("Please sign in with Google to use the application.")
        authenticate()

if __name__ == "__main__":
    main()