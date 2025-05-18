# frontend/components/auth.py
import streamlit as st
import requests
import time
from src.app.frontend.utils.api_helper import API_BASE_URL, get_auth_url, process_auth_callback

def authenticate():
    """Start the authentication process"""
    try:
        auth_url = get_auth_url()
        if auth_url:
            st.markdown(f"""
            ### Please authenticate with Google
            
            1. Click the link below to authenticate with Google.
            2. After authentication, copy the full URL you are redirected to.
            3. Paste the URL in the text box below.
            
            [Click here to authenticate with Google]({auth_url})
            """, unsafe_allow_html=True)
            
            with st.form("auth_code_form"):
                auth_code = st.text_input("Enter the authorization code")
                submit = st.form_submit_button("Submit")
                
                if submit and auth_code:
                    result = process_auth_callback(auth_code)
                    if result["success"]:
                        st.success("Authentication successful!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(result["message"])
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")

def logout():
    """Log out the user"""
    st.session_state.is_authenticated = False
    st.session_state.access_token = None
    st.session_state.sheets = []
    st.session_state.columns = []
    st.session_state.generated_doc_id = None
    st.success("Logged out successfully!")
    time.sleep(1)
    st.rerun()

def display_auth_status():
    """Display authentication status and login/logout buttons"""
    auth_col1, auth_col2 = st.columns([3, 1])
    with auth_col1:
        if st.session_state.is_authenticated:
            st.success("✅ Authenticated with Google")
            # Show token expiry if available
            from src.app.services.token_store import TokenStore
            tokens = TokenStore.get_latest_tokens()
            if tokens and tokens.get('expiry'):
                st.info(f"Token valid until: {tokens.get('expiry')}")
        else:
            st.warning("⚠️ Not authenticated - Please sign in with Google")
            # Check if token.json exists but was not loaded
            import os
            from src.app.services.token_store import TOKEN_FILE
            if os.path.exists(TOKEN_FILE):
                st.info("A token file exists but could not be loaded. You may need to re-authenticate.")
    
    with auth_col2:
        if st.session_state.is_authenticated:
            st.button("Logout", on_click=logout)
        else:
            st.button("Sign in with Google", on_click=authenticate)