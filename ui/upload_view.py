"""Upload view for file upload functionality."""

import streamlit as st
from typing import Optional, Tuple, Dict, Any
import tempfile
import os


def render_upload_view() -> Optional[Dict[str, Any]]:
    """
    Render the upload view.
    
    Returns:
        Dict with uploaded file info or None if not uploaded
    """
    st.markdown("### Upload Workbook")
    st.markdown(
        "<p style='color: #5f6368; margin-bottom: 24px;'>Upload an Excel file to begin cleaning your data.</p>",
        unsafe_allow_html=True
    )
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["xlsx", "csv"],
        help="Supported formats: .xlsx, .csv",
        key="file_uploader"
    )
    
    if uploaded_file is not None:
        # Display file info
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info(f"**File:** {uploaded_file.name}")
        
        with col2:
            st.info(f"**Size:** {_format_size(uploaded_file.size)}")
        
        with col3:
            st.info(f"**Type:** {uploaded_file.type}")
        
        # Save to temp file and return path
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        return {
            "name": uploaded_file.name,
            "path": temp_path,
            "size": uploaded_file.size,
            "type": uploaded_file.type,
        }
    
    # Show instructions when no file uploaded
    st.markdown("""
    <div style='margin-top: 40px; padding: 30px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dadce0;'>
        <h4 style='margin-top: 0;'>Supported File Types</h4>
        <ul style='color: #5f6368;'>
            <li><strong>.xlsx</strong> - Excel Workbook (recommended)</li>
            <li><strong>.csv</strong> - Comma-Separated Values</li>
        </ul>
        
        <h4>What happens next?</h4>
        <ol style='color: #5f6368;'>
            <li>Your file will be scanned for all unique values</li>
            <li>You'll see frequency counts and where each value appears</li>
            <li>Create cleaning rules to replace or standardize values</li>
            <li>Preview changes before exporting</li>
            <li>Export cleaned workbook and statistics</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    
    return None


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def render_upload_success_message(filename: str) -> None:
    """
    Render success message after upload.
    
    Args:
        filename: Name of uploaded file
    """
    st.success(f"✓ File '{filename}' uploaded successfully!")
    st.info("Click 'Scan Workbook' in the navigation to analyze your data.")
