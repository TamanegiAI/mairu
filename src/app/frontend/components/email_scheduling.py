# frontend/components/email_scheduling.py
import streamlit as st
from datetime import datetime
from src.app.frontend.utils.api_helper import send_email, schedule_email, get_scheduled_emails, cancel_scheduled_email

def display_email_config():
    """Display email configuration UI"""
    st.header("Email Configuration")
            
    st.session_state.row_index = st.number_input(
        "Data Row (0 is header)", 
        min_value=1, 
        value=1
    )
    
    st.session_state.email_to = st.text_input("To:", placeholder="recipient@example.com")
    st.session_state.email_cc = st.text_input("CC:", placeholder="cc@example.com")
    st.session_state.email_subject = st.text_input("Subject:")
    st.session_state.email_body = st.text_area("Body:")

def display_send_schedule():
    """Display send and schedule email UI"""
    st.header("Send or Schedule")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.session_state.generated_doc_id:
            st.subheader("Send Email")
            if st.button("Send Email Now"):
                if send_email(
                    st.session_state.email_to,
                    st.session_state.email_subject,
                    st.session_state.email_body,
                    st.session_state.access_token,
                    st.session_state.email_cc,
                    st.session_state.generated_doc_id
                ):
                    st.success("Email sent successfully!")
        else:
            st.info("Generate a document first before sending.")
    
    with col2:
        if st.session_state.generated_doc_id:
            st.subheader("Schedule Email")
            scheduled_date = st.date_input("Schedule Date")
            scheduled_time = st.time_input("Schedule Time")
            
            # Combine date and time
            scheduled_datetime = datetime.combine(scheduled_date, scheduled_time)
            
            if st.button("Schedule Email"):
                if schedule_email(
                    st.session_state.email_to,
                    st.session_state.email_subject,
                    st.session_state.email_body,
                    scheduled_datetime.isoformat(),
                    st.session_state.access_token,
                    st.session_state.email_cc,
                    st.session_state.generated_doc_id
                ):
                    st.success(f"Email scheduled for {scheduled_datetime.strftime('%Y-%m-%d %H:%M')}!")
        else:
            st.info("Generate a document first before scheduling.")
            
    # Scheduled emails section
    st.header("Scheduled Emails")
    if st.button("Refresh"):
        st.session_state.scheduled_emails = get_scheduled_emails(st.session_state.access_token)
        
    if 'scheduled_emails' not in st.session_state:
        st.session_state.scheduled_emails = get_scheduled_emails(st.session_state.access_token)
        
    if st.session_state.scheduled_emails:
        for email in st.session_state.scheduled_emails:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Time:** {email['scheduled_time']}")
                st.write(f"**Status:** {email['status']}")
            
            with col2:
                if email['status'] == 'pending':
                    if st.button("Cancel", key=f"cancel_{email['job_id']}"):
                        result = cancel_scheduled_email(email['job_id'], st.session_state.access_token)
                        if result.get('success', False):
                            st.success("Email cancelled")
                            # Refresh the list
                            st.session_state.scheduled_emails = get_scheduled_emails(st.session_state.access_token)
                            st.experimental_rerun()
            st.divider()
    else:
        st.info("No scheduled emails found.")