"""Custom CSS theme for premium desktop feel."""


def get_custom_css() -> str:
    """Return custom CSS for the application."""
    return """
    <style>
    /* Root variables for consistent theming */
    :root {
        --bg-primary: #f8f9fa;
        --bg-secondary: #ffffff;
        --bg-tertiary: #f1f3f4;
        --text-primary: #202124;
        --text-secondary: #5f6368;
        --text-tertiary: #80868b;
        --border-color: #dadce0;
        --accent-color: #1a73e8;
        --accent-hover: #1557b0;
        --success-color: #188038;
        --warning-color: #f9ab00;
        --error-color: #d93025;
        --shadow-sm: 0 1px 2px rgba(60,64,67,0.1);
        --shadow-md: 0 2px 6px rgba(60,64,67,0.15);
        --shadow-lg: 0 4px 12px rgba(60,64,67,0.2);
        --radius-sm: 6px;
        --radius-md: 8px;
        --radius-lg: 12px;
    }
    
    /* Page background */
    .stApp {
        background-color: var(--bg-primary);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Top bar styling */
    .top-bar {
        background: var(--bg-secondary);
        border-bottom: 1px solid var(--border-color);
        padding: 12px 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: var(--shadow-sm);
        position: sticky;
        top: 0;
        z-index: 100;
    }
    
    .app-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0;
    }
    
    /* Left navigation rail */
    .nav-rail {
        background: var(--bg-secondary);
        border-right: 1px solid var(--border-color);
        padding: 16px 8px;
        min-height: calc(100vh - 60px);
        position: fixed;
        left: 0;
        top: 60px;
        width: 200px;
        z-index: 99;
    }
    
    .nav-item {
        padding: 10px 16px;
        margin: 4px 8px;
        border-radius: var(--radius-md);
        cursor: pointer;
        transition: all 0.2s ease;
        color: var(--text-secondary);
        font-size: 0.9rem;
        font-weight: 500;
    }
    
    .nav-item:hover {
        background: var(--bg-tertiary);
        color: var(--text-primary);
    }
    
    .nav-item.active {
        background: #e8f0fe;
        color: var(--accent-color);
    }
    
    /* Main workspace */
    .main-workspace {
        margin-left: 220px;
        margin-top: 70px;
        padding: 24px;
        max-width: 1400px;
    }
    
    /* Card/panel styling */
    .data-card {
        background: var(--bg-secondary);
        border-radius: var(--radius-lg);
        border: 1px solid var(--border-color);
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: var(--shadow-sm);
    }
    
    .card-header {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--border-color);
    }
    
    /* Summary cards grid */
    .summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }
    
    .summary-card {
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
        border: 1px solid var(--border-color);
        padding: 16px;
        text-align: center;
    }
    
    .summary-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--accent-color);
    }
    
    .summary-label {
        font-size: 0.85rem;
        color: var(--text-secondary);
        margin-top: 4px;
    }
    
    /* Table styling */
    .data-table-container {
        background: var(--bg-secondary);
        border-radius: var(--radius-md);
        border: 1px solid var(--border-color);
        overflow: hidden;
    }
    
    .data-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
    }
    
    .data-table th {
        background: var(--bg-tertiary);
        padding: 12px 16px;
        text-align: left;
        font-weight: 600;
        color: var(--text-primary);
        border-bottom: 2px solid var(--border-color);
    }
    
    .data-table td {
        padding: 10px 16px;
        border-bottom: 1px solid var(--border-color);
        color: var(--text-secondary);
    }
    
    .data-table tr:hover {
        background: var(--bg-tertiary);
    }
    
    /* Changed cell highlighting */
    .changed-cell {
        background-color: #fff8dc !important;
        color: #b7791f !important;
        font-weight: 500;
    }
    
    .changed-cell-new {
        background-color: #d4edda !important;
        color: #155724 !important;
        font-weight: 500;
    }
    
    /* Button styling */
    .stButton > button {
        background: var(--accent-color);
        color: white;
        border: none;
        border-radius: var(--radius-sm);
        padding: 8px 16px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background: var(--accent-hover);
        box-shadow: var(--shadow-md);
    }
    
    /* Input styling */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        border: 1px solid var(--border-color);
        border-radius: var(--radius-sm);
        padding: 8px 12px;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--accent-color);
        box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2);
    }
    
    /* Select box styling */
    .stSelectbox > div > div > select {
        border: 1px solid var(--border-color);
        border-radius: var(--radius-sm);
        padding: 8px 12px;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .status-success {
        background: #d4edda;
        color: #155724;
    }
    
    .status-warning {
        background: #fff3cd;
        color: #856404;
    }
    
    .status-info {
        background: #d1ecf1;
        color: #0c5460;
    }
    
    /* Upload area */
    .upload-area {
        border: 2px dashed var(--border-color);
        border-radius: var(--radius-lg);
        padding: 40px;
        text-align: center;
        background: var(--bg-secondary);
        transition: all 0.2s ease;
    }
    
    .upload-area:hover {
        border-color: var(--accent-color);
        background: #f8fbff;
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-tertiary);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--text-tertiary);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-secondary);
    }
    
    /* RTL support for Arabic */
    [dir="rtl"] {
        direction: rtl;
        text-align: right;
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
        .nav-rail {
            width: 60px;
            padding: 16px 4px;
        }
        
        .nav-item span {
            display: none;
        }
        
        .main-workspace {
            margin-left: 70px;
        }
        
        .summary-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }
    </style>
    """


def inject_custom_css():
    """Inject custom CSS into the Streamlit app."""
    import streamlit as st
    st.markdown(get_custom_css(), unsafe_allow_html=True)
