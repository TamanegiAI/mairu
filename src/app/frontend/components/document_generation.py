# frontend/components/document_generation.py
import streamlit as st
from src.app.frontend.utils.api_helper import generate_document

def display_generation_tab():
    """Display UI for document generation preview"""
    st.header("Generate Document")
    
    # Check prerequisites
    if ('selected_sheet_id' not in st.session_state or 
        'selected_template_id' not in st.session_state or 
        'column_mappings' not in st.session_state or 
        len(st.session_state.column_mappings) < 1):
        st.warning("Please complete the previous steps first")
        return
    
    st.write(f"**Sheet:** {st.session_state.selected_sheet_name}")
    st.write(f"**Template:** {st.session_state.selected_template_name}")
    st.write("**Mappings:**")
    
    # Display the mappings in a nice format
    mapping_data = []
    for placeholder, column in st.session_state.column_mappings.items():
        mapping_data.append({"Placeholder": f"{{{{{placeholder}}}}}", "Sheet Column": column})
    
    if mapping_data:
        st.table(mapping_data)
    
    # Row selection for document generation
    st.write("### Select Row to Generate Document")
    row_index = st.number_input(
        "Row Number (starting from 1, excluding header row):", 
        min_value=1, 
        value=1, 
        step=1
    )
    
    if st.button("Generate Document"):
        with st.spinner("Generating document..."):
            result = generate_document(
                st.session_state.selected_sheet_id,
                st.session_state.selected_template_id,
                row_index,  # API expects 0-indexed row, but UI is 1-indexed
                st.session_state.access_token
            )
            
            if result.get("success"):
                st.session_state.generated_doc_id = result.get("document_id")
                st.session_state.generated_doc_title = result.get("document_title")
                st.success(f"✅ Document generated successfully: {result.get('document_title')}")
                
                # Display link to the document
                doc_link = f"https://docs.google.com/document/d/{result.get('document_id')}/edit"
                st.markdown(f"[Open Document in Google Docs]({doc_link})")
                
                # Go to Email tab
                st.button("Continue to Email Configuration →", 
                        on_click=lambda: st.session_state.update(current_tab=3))
            else:
                st.error(f"Failed to generate document: {result.get('detail', 'Unknown error')}")