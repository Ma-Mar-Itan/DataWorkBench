"""
Spreadsheet Cleaner - Main Application

A professional Streamlit web application for cleaning Excel spreadsheet data.
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from models.schemas import Rule
from core import (
    load_workbook,
    scan_workbook,
    apply_rules,
)
from ui import (
    inject_custom_css,
    render_nav_rail,
    render_upload_view,
    render_scan_view,
    render_rules_view,
    render_preview_view,
    render_stats_view,
    render_export_view,
    render_empty_state,
    render_error_message,
    render_success_message,
)


def initialize_session_state():
    """Initialize session state variables."""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "upload"
    
    if "sheets" not in st.session_state:
        st.session_state.sheets = None
    
    if "metadata" not in st.session_state:
        st.session_state.metadata = None
    
    if "value_index" not in st.session_state:
        st.session_state.value_index = None
    
    if "rules" not in st.session_state:
        st.session_state.rules = []
    
    if "file_uploaded" not in st.session_state:
        st.session_state.file_uploaded = False
    
    if "show_load_dialog" not in st.session_state:
        st.session_state.show_load_dialog = False


def main():
    """Main application entry point."""
    # Page configuration
    st.set_page_config(
        page_title="Spreadsheet Cleaner",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # Inject custom CSS
    inject_custom_css()
    
    # Initialize session state
    initialize_session_state()
    
    # Render navigation
    selected_page = render_nav_rail(st.session_state.current_page)
    
    if selected_page != st.session_state.current_page:
        st.session_state.current_page = selected_page
        st.rerun()
    
    # Route to appropriate view
    if st.session_state.current_page == "upload":
        render_upload_page()
    elif st.session_state.current_page == "scan":
        render_scan_page()
    elif st.session_state.current_page == "rules":
        render_rules_page()
    elif st.session_state.current_page == "preview":
        render_preview_page()
    elif st.session_state.current_page == "stats":
        render_stats_page()
    elif st.session_state.current_page == "export":
        render_export_page()


def render_upload_page():
    """Render the upload page."""
    st.markdown("<div class='main-workspace'>", unsafe_allow_html=True)
    
    file_info = render_upload_view()
    
    if file_info:
        st.session_state.file_info = file_info
        st.session_state.file_uploaded = True
        
        # Auto-scan after upload
        with st.spinner("Loading workbook..."):
            try:
                sheets, metadata = load_workbook(file_info["path"])
                st.session_state.sheets = sheets
                st.session_state.metadata = metadata
                
                # Scan workbook
                value_index = scan_workbook(sheets)
                st.session_state.value_index = value_index
                
                st.success(f"✓ Workbook loaded: {len(sheets)} sheet(s), {metadata.get('total_cells', 0)} cells")
                st.info("Navigate to 'Scan Results' to view your data.")
                
            except Exception as e:
                render_error_message(f"Error loading workbook: {e}")
    
    st.markdown("</div>", unsafe_allow_html=True)


def render_scan_page():
    """Render the scan results page."""
    st.markdown("<div class='main-workspace'>", unsafe_allow_html=True)
    
    if not st.session_state.file_uploaded or not st.session_state.value_index:
        render_empty_state(
            "No workbook uploaded. Please upload a file first.",
            "Go to Upload",
            lambda: setattr(st.session_state, 'current_page', 'upload')
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    render_scan_view(
        st.session_state.value_index,
        st.session_state.metadata or {},
        st.session_state.sheets or {}
    )
    
    st.markdown("</div>", unsafe_allow_html=True)


def render_rules_page():
    """Render the cleaning rules page."""
    st.markdown("<div class='main-workspace'>", unsafe_allow_html=True)
    
    if not st.session_state.file_uploaded or not st.session_state.value_index:
        render_empty_state(
            "No workbook uploaded. Please upload a file first.",
            "Go to Upload",
            lambda: setattr(st.session_state, 'current_page', 'upload')
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    updated_rules = render_rules_view(
        st.session_state.value_index,
        st.session_state.metadata or {},
        st.session_state.rules
    )
    
    st.session_state.rules = updated_rules
    
    st.markdown("</div>", unsafe_allow_html=True)


def render_preview_page():
    """Render the preview page."""
    st.markdown("<div class='main-workspace'>", unsafe_allow_html=True)
    
    if not st.session_state.file_uploaded or not st.session_state.sheets:
        render_empty_state(
            "No workbook uploaded. Please upload a file first.",
            "Go to Upload",
            lambda: setattr(st.session_state, 'current_page', 'upload')
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    render_preview_view(
        st.session_state.sheets,
        st.session_state.rules,
        st.session_state.metadata or {}
    )
    
    st.markdown("</div>", unsafe_allow_html=True)


def render_stats_page():
    """Render the statistics page."""
    st.markdown("<div class='main-workspace'>", unsafe_allow_html=True)
    
    if not st.session_state.file_uploaded or not st.session_state.sheets:
        render_empty_state(
            "No workbook uploaded. Please upload a file first.",
            "Go to Upload",
            lambda: setattr(st.session_state, 'current_page', 'upload')
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    render_stats_view(
        st.session_state.sheets,
        st.session_state.rules,
        st.session_state.metadata or {}
    )
    
    st.markdown("</div>", unsafe_allow_html=True)


def render_export_page():
    """Render the export page."""
    st.markdown("<div class='main-workspace'>", unsafe_allow_html=True)
    
    if not st.session_state.file_uploaded or not st.session_state.sheets:
        render_empty_state(
            "No workbook uploaded. Please upload a file first.",
            "Go to Upload",
            lambda: setattr(st.session_state, 'current_page', 'upload')
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    render_export_view(
        st.session_state.sheets,
        st.session_state.rules,
        st.session_state.metadata or {}
    )
    
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
