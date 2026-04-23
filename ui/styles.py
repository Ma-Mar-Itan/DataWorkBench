"""
Custom CSS for the data cleaning app.

Inspired by desktop productivity apps (see reference screenshot):
  - soft gray canvas with rounded near-white panels floating on top
  - a horizontal top bar with a dominant, search-led feel
  - a quiet left rail with clear active state
  - restrained, serious accent color
  - disciplined spacing, minimal shadows, subtle dividers
"""

CSS = """
<style>

/* ---------- Design tokens ---------------------------------------- */
:root {
    --bg:            #f3f4f6;          /* app canvas */
    --bg-subtle:     #eceef1;
    --panel:         #ffffff;
    --panel-soft:    #fafbfc;
    --border:        #e4e6ea;
    --border-strong: #d5d8de;
    --divider:       #eef0f3;

    --text:          #1f2430;
    --text-muted:    #5b6472;
    --text-faint:    #8a93a2;

    --accent:        #2d5cbb;          /* restrained blue */
    --accent-soft:   #e7eefa;
    --accent-strong: #1f4593;

    --success:       #2f8a5f;
    --success-soft:  #e5f3ec;
    --warn:          #b47216;
    --warn-soft:     #fbf1dc;
    --danger:        #b5383a;
    --danger-soft:   #fbe8e8;

    --radius-sm:     6px;
    --radius-md:     10px;
    --radius-lg:     14px;

    --shadow-sm:     0 1px 2px rgba(16, 24, 40, 0.04);
    --shadow-md:     0 2px 6px rgba(16, 24, 40, 0.05), 0 1px 2px rgba(16, 24, 40, 0.04);

    --font-sans:     "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI",
                     Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* ---------- Global ------------------------------------------------ */
html, body, [class*="css"] {
    font-family: var(--font-sans);
    color: var(--text);
}

.stApp {
    background: var(--bg);
}

/* Suppress default Streamlit chrome */
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }

/* Kill Streamlit's deploy button overlap */
.stDeployButton { display: none; }

/* Main container: pull content up, widen, tighten gutters */
.block-container {
    padding-top: 0.4rem !important;
    padding-bottom: 2.5rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 100% !important;
}

/* ---------- Top app bar ------------------------------------------ */
.topbar {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 10px 18px;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 18px;
    box-shadow: var(--shadow-sm);
    min-height: 56px;
}

.topbar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 220px;
}

.topbar-brand .logo {
    width: 28px;
    height: 28px;
    border-radius: 7px;
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-strong) 100%);
    display: grid;
    place-items: center;
    color: #fff;
    font-weight: 700;
    font-size: 14px;
    letter-spacing: -0.02em;
    box-shadow: inset 0 -1px 0 rgba(0,0,0,0.08);
}

.topbar-brand .name {
    font-weight: 600;
    font-size: 15.5px;
    color: var(--text);
    letter-spacing: -0.01em;
}

.topbar-brand .tag {
    font-size: 11px;
    color: var(--text-faint);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding-top: 1px;
}

.topbar-search {
    flex: 1;
    max-width: 720px;
}

.topbar-right {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-left: auto;
}

.scan-indicator {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 12.5px;
    color: var(--text-muted);
    background: var(--panel-soft);
    border: 1px solid var(--border);
    padding: 6px 12px;
    border-radius: 999px;
    font-weight: 500;
}
.scan-indicator .dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--text-faint);
    box-shadow: 0 0 0 3px rgba(138,147,162,0.12);
}
.scan-indicator.ok  .dot { background: var(--success); box-shadow: 0 0 0 3px rgba(47,138,95,0.16); }
.scan-indicator.run .dot { background: var(--warn);    box-shadow: 0 0 0 3px rgba(180,114,22,0.16); animation: pulse 1.4s infinite; }

@keyframes pulse {
    0%,100% { opacity: 1; }
    50%     { opacity: 0.4; }
}

/* ---------- Left navigation rail --------------------------------- */
.navrail {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 14px 10px;
    box-shadow: var(--shadow-sm);
    min-height: calc(100vh - 120px);
}

.navrail-heading {
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-faint);
    font-weight: 600;
    padding: 10px 10px 6px 10px;
}

/* Turn Streamlit radio into a nav list */
.navrail div[role="radiogroup"] {
    gap: 2px !important;
    display: flex;
    flex-direction: column;
}

.navrail div[role="radiogroup"] > label {
    padding: 9px 11px !important;
    border-radius: 8px !important;
    cursor: pointer;
    transition: background 120ms ease;
    border: 1px solid transparent;
    margin: 0 !important;
}

.navrail div[role="radiogroup"] > label:hover {
    background: var(--bg-subtle);
}

.navrail div[role="radiogroup"] > label > div:first-child {
    display: none !important;          /* hide the radio circle */
}

.navrail div[role="radiogroup"] > label p {
    font-size: 13.5px !important;
    font-weight: 500 !important;
    color: var(--text-muted) !important;
    margin: 0 !important;
}

/* active nav item */
.navrail div[role="radiogroup"] > label:has(input:checked) {
    background: var(--accent-soft);
    border-color: #cfdcf3;
}
.navrail div[role="radiogroup"] > label:has(input:checked) p {
    color: var(--accent-strong) !important;
    font-weight: 600 !important;
}

/* ---------- Panels ----------------------------------------------- */
.panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 20px 22px;
    box-shadow: var(--shadow-sm);
    margin-bottom: 14px;
}

.panel-soft {
    background: var(--panel-soft);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 18px 20px;
}

.panel-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
    letter-spacing: -0.005em;
    margin: 0 0 2px 0;
}
.panel-subtitle {
    font-size: 12.5px;
    color: var(--text-muted);
    margin: 0 0 14px 0;
}

.section-eyebrow {
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-faint);
    font-weight: 600;
    margin-bottom: 4px;
}

.page-title {
    font-size: 20px;
    font-weight: 600;
    letter-spacing: -0.015em;
    color: var(--text);
    margin: 2px 0 2px 0;
}

.page-sub {
    font-size: 13.5px;
    color: var(--text-muted);
    margin-bottom: 16px;
}

/* ---------- Summary stat cards ----------------------------------- */
.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px;
    margin-bottom: 14px;
}

.stat-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 14px 16px 14px 16px;
    box-shadow: var(--shadow-sm);
    display: flex;
    flex-direction: column;
    gap: 2px;
}
.stat-card .label {
    font-size: 11.5px;
    color: var(--text-faint);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
}
.stat-card .value {
    font-size: 22px;
    font-weight: 600;
    color: var(--text);
    letter-spacing: -0.015em;
    line-height: 1.15;
}
.stat-card .delta {
    font-size: 11.5px;
    color: var(--text-muted);
    margin-top: 2px;
}
.stat-card .delta.pos { color: var(--success); }
.stat-card .delta.neg { color: var(--danger); }

/* ---------- Badges / chips --------------------------------------- */
.chip {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 500;
    background: var(--bg-subtle);
    color: var(--text-muted);
    border: 1px solid var(--border);
    line-height: 1.5;
}
.chip.accent  { background: var(--accent-soft);  color: var(--accent-strong); border-color: #cfdcf3; }
.chip.success { background: var(--success-soft); color: var(--success);       border-color: #c9e4d6; }
.chip.warn    { background: var(--warn-soft);    color: var(--warn);          border-color: #eed9ae; }
.chip.danger  { background: var(--danger-soft);  color: var(--danger);        border-color: #ecc6c6; }

.count-badge {
    display: inline-block;
    min-width: 24px;
    padding: 1px 8px;
    text-align: center;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 600;
    background: var(--bg-subtle);
    color: var(--text-muted);
}

/* ---------- Inputs ----------------------------------------------- */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background: var(--panel-soft) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    font-size: 13.5px !important;
    color: var(--text) !important;
    transition: border-color 120ms ease, box-shadow 120ms ease;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(45,92,187,0.12) !important;
    outline: none !important;
}

.stTextInput label, .stSelectbox label, .stNumberInput label, .stMultiSelect label, .stFileUploader label {
    font-size: 12px !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* Searchbar variant used in top bar */
.searchbar-wrap .stTextInput > div > div > input {
    background: var(--bg-subtle) !important;
    border: 1px solid transparent !important;
    padding: 10px 14px 10px 38px !important;
    font-size: 14px !important;
    border-radius: 10px !important;
}
.searchbar-wrap { position: relative; }
.searchbar-wrap::before {
    content: "";
    position: absolute;
    top: 50%;
    left: 13px;
    transform: translateY(-50%);
    width: 14px; height: 14px;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%238a93a2' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'><circle cx='11' cy='11' r='7'/><path d='m21 21-4.3-4.3'/></svg>");
    background-repeat: no-repeat;
    z-index: 2;
    pointer-events: none;
}

/* ---------- Buttons ---------------------------------------------- */
.stButton > button {
    background: var(--panel);
    color: var(--text);
    border: 1px solid var(--border-strong);
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 500;
    transition: background 120ms ease, border-color 120ms ease;
    box-shadow: var(--shadow-sm);
}
.stButton > button:hover {
    background: var(--bg-subtle);
    border-color: var(--text-faint);
    color: var(--text);
}
.stButton > button:focus:not(:active) {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(45,92,187,0.12);
    color: var(--text);
}

/* primary button variant — use kind="primary" */
.stButton > button[kind="primary"] {
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
}
.stButton > button[kind="primary"]:hover {
    background: var(--accent-strong);
    border-color: var(--accent-strong);
    color: #fff;
}

/* download buttons match primary action look */
.stDownloadButton > button {
    background: var(--accent);
    color: #fff;
    border: 1px solid var(--accent);
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 500;
    box-shadow: var(--shadow-sm);
}
.stDownloadButton > button:hover { background: var(--accent-strong); color: #fff; }

/* ---------- File uploader ---------------------------------------- */
[data-testid="stFileUploader"] section {
    background: var(--panel-soft);
    border: 1.5px dashed var(--border-strong);
    border-radius: var(--radius-md);
    padding: 32px 20px !important;
    transition: border-color 120ms ease, background 120ms ease;
}
[data-testid="stFileUploader"] section:hover {
    border-color: var(--accent);
    background: var(--accent-soft);
}
[data-testid="stFileUploader"] button {
    background: var(--panel) !important;
    color: var(--text) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
}

/* ---------- Tabs ------------------------------------------------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    background: var(--bg-subtle);
    padding: 3px;
    border-radius: 8px;
    border: 1px solid var(--border);
    width: fit-content;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 6px;
    padding: 6px 14px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: var(--text-muted) !important;
    border: none !important;
    height: auto !important;
}
.stTabs [aria-selected="true"] {
    background: var(--panel) !important;
    color: var(--text) !important;
    box-shadow: var(--shadow-sm);
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"]    { display: none; }

/* ---------- Data editor / tables --------------------------------- */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--panel);
    overflow: hidden;
}

/* Dataframe headers */
[data-testid="stDataFrame"] thead th,
[data-testid="stDataEditor"] thead th {
    background: var(--panel-soft) !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* ---------- Dividers --------------------------------------------- */
hr, [data-testid="stDivider"] {
    border: none;
    border-top: 1px solid var(--divider);
    margin: 14px 0;
}

/* ---------- Metrics ---------------------------------------------- */
[data-testid="stMetric"] {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 14px 16px;
    box-shadow: var(--shadow-sm);
}
[data-testid="stMetricLabel"] p {
    font-size: 11.5px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    color: var(--text-faint) !important;
}
[data-testid="stMetricValue"] {
    font-size: 22px !important;
    font-weight: 600 !important;
    letter-spacing: -0.015em !important;
}

/* ---------- Alerts ----------------------------------------------- */
.stAlert {
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
    font-size: 13px;
}

/* ---------- Expanders -------------------------------------------- */
.streamlit-expanderHeader, [data-testid="stExpander"] summary {
    background: var(--panel-soft) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 13.5px !important;
}
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-md) !important;
    box-shadow: var(--shadow-sm);
}

/* ---------- Toolbar row under top bar ---------------------------- */
.toolbar-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
}
.toolbar-row .title-block { display: flex; flex-direction: column; gap: 2px; }
.toolbar-row .actions { display: flex; gap: 8px; align-items: center; }

/* ---------- Key/value description list --------------------------- */
.kv {
    display: grid;
    grid-template-columns: 110px 1fr;
    row-gap: 4px;
    font-size: 13px;
}
.kv dt {
    color: var(--text-faint);
    font-size: 11.5px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
    padding-top: 2px;
}
.kv dd { margin: 0; color: var(--text); font-weight: 500; }

/* ---------- Progress lines --------------------------------------- */
.bar {
    background: var(--bg-subtle);
    border-radius: 999px;
    height: 6px;
    overflow: hidden;
}
.bar > span { display: block; height: 100%; background: var(--accent); border-radius: 999px; }
.bar.warn  > span { background: var(--warn); }
.bar.ok    > span { background: var(--success); }

/* ---------- Hide label for disguised inputs ---------------------- */
.visually-hidden-label label { display: none; }

</style>
"""
