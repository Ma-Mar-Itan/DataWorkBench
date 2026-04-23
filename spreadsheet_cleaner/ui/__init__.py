"""UI module __init__.py"""

from .theme import get_custom_css, inject_custom_css
from .layout import (
    render_top_bar,
    render_nav_rail,
    render_summary_cards,
    render_data_card,
    render_section_header,
    render_empty_state,
    render_error_message,
    render_success_message,
    render_warning_message,
    render_info_message,
)
from .upload_view import render_upload_view, render_upload_success_message
from .scan_view import render_scan_view, render_scan_summary
from .rules_view import render_rules_view, render_quick_add_buttons
from .preview_view import render_preview_view, render_quick_preview, get_preview_summary
from .stats_view import render_stats_view, get_stats_summary
from .export_view import render_export_view, render_quick_export, get_export_ready_data

__all__ = [
    # Theme
    "get_custom_css",
    "inject_custom_css",
    # Layout
    "render_top_bar",
    "render_nav_rail",
    "render_summary_cards",
    "render_data_card",
    "render_section_header",
    "render_empty_state",
    "render_error_message",
    "render_success_message",
    "render_warning_message",
    "render_info_message",
    # Views
    "render_upload_view",
    "render_upload_success_message",
    "render_scan_view",
    "render_scan_summary",
    "render_rules_view",
    "render_quick_add_buttons",
    "render_preview_view",
    "render_quick_preview",
    "get_preview_summary",
    "render_stats_view",
    "get_stats_summary",
    "render_export_view",
    "render_quick_export",
    "get_export_ready_data",
]
