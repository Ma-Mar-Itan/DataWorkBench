"""Layout components for the application."""

import streamlit as st


def render_top_bar(app_title: str = "Spreadsheet Cleaner", 
                   show_status: bool = False,
                   status_text: str = "") -> None:
    """
    Render the top navigation bar.
    
    Args:
        app_title: Title to display
        show_status: Whether to show status indicator
        status_text: Status text to display
    """
    # Use columns for layout
    col1, col2, col3 = st.columns([3, 1, 2])
    
    with col1:
        st.markdown(f"<h2 style='margin: 0; font-size: 1.4rem; color: #202124;'>{app_title}</h2>", 
                    unsafe_allow_html=True)
    
    with col2:
        if show_status and status_text:
            st.markdown(
                f"<span class='status-badge status-success'>{status_text}</span>",
                unsafe_allow_html=True
            )
    
    with col3:
        # Placeholder for future actions (settings, help, etc.)
        pass


def render_nav_rail(current_page: str = "upload") -> str:
    """
    Render the left navigation rail.
    
    Args:
        current_page: Current active page
        
    Returns:
        Selected page from nav clicks
    """
    nav_items = [
        ("upload", "📁 Upload"),
        ("scan", "🔍 Scan Results"),
        ("rules", "✏️ Cleaning Rules"),
        ("preview", "👁️ Preview"),
        ("stats", "📊 Statistics"),
        ("export", "💾 Export"),
    ]
    
    selected = st.sidebar.radio(
        "Navigation",
        [label for _, label in nav_items],
        index=[item[0] for item in nav_items].index(current_page) if current_page in [item[0] for item in nav_items] else 0,
        label_visibility="collapsed"
    )
    
    # Map back to page key
    for key, label in nav_items:
        if selected == label:
            return key
    
    return current_page


def render_summary_cards(metrics: dict) -> None:
    """
    Render summary metric cards.
    
    Args:
        metrics: Dict of metric_name -> value
    """
    cols = st.columns(min(len(metrics), 5))
    
    for idx, (label, value) in enumerate(metrics.items()):
        with cols[idx % len(cols)]:
            st.metric(
                label=label.replace("_", " ").title(),
                value=value,
            )


def render_data_card(title: str, content: str = "", key: str = "") -> None:
    """
    Render a data card/panel.
    
    Args:
        title: Card title
        content: Optional content
        key: Unique key for the card
    """
    st.markdown(f"""
    <div class="data-card" id="{key}">
        <div class="card-header">{title}</div>
        {content}
    </div>
    """, unsafe_allow_html=True)


def render_section_header(title: str, subtitle: str = "") -> None:
    """
    Render a section header.
    
    Args:
        title: Main title
        subtitle: Optional subtitle
    """
    st.markdown(f"### {title}")
    if subtitle:
        st.markdown(f"<p style='color: #5f6368; margin-top: -16px; margin-bottom: 20px;'>{subtitle}</p>",
                    unsafe_allow_html=True)


def render_empty_state(message: str, action_label: str = "", action_callback=None) -> None:
    """
    Render an empty state message.
    
    Args:
        message: Message to display
        action_label: Optional action button label
        action_callback: Optional callback for action
    """
    st.markdown(f"""
    <div style='text-align: center; padding: 60px 20px; color: #5f6368;'>
        <p style='font-size: 1.1rem;'>{message}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if action_label and action_callback:
        if st.button(action_label):
            action_callback()


def render_error_message(message: str) -> None:
    """
    Render an error message.
    
    Args:
        message: Error message
    """
    st.error(message)


def render_success_message(message: str) -> None:
    """
    Render a success message.
    
    Args:
        message: Success message
    """
    st.success(message)


def render_warning_message(message: str) -> None:
    """
    Render a warning message.
    
    Args:
        message: Warning message
    """
    st.warning(message)


def render_info_message(message: str) -> None:
    """
    Render an info message.
    
    Args:
        message: Info message
    """
    st.info(message)
